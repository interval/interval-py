import asyncio, sys
import inspect
from asyncio.futures import Future
from typing import (
    Any,
    Callable,
    Generic,
    Optional,
    Union,
    cast,
)
from typing_extensions import TypeVarTuple, Unpack, TypeAlias, Awaitable, TypeVar


from pydantic import parse_obj_as, ValidationError, BaseModel as PydanticBaseModel

from ..io_schema import (
    ButtonConfig,
    ComponentMultipleProps,
    MethodDef,
    MN,
    io_schema,
    ComponentRenderInfo,
)
from ..types import GenericModel
from ..util import dict_keys_to_snake, dict_strip_none, dict_keys_to_camel

Output_co = TypeVar("Output_co", covariant=True)
GroupOutput = TypeVarTuple("GroupOutput")

IOPromiseValidator: TypeAlias = Callable[
    [Output_co], Union[Awaitable[Optional[str]], str, None]
]
IOGroupPromiseValidator: TypeAlias = Callable[
    [Unpack[GroupOutput]], Union[Awaitable[Optional[str]], str, None]
]


class ComponentInstance(GenericModel, Generic[MN]):
    method_name: MN
    label: str
    # TODO: Try typing these
    props: dict[str, Any] = {}
    state: Optional[dict[str, Any]] = None
    is_stateful: bool = False
    is_optional: bool = False
    is_multiple: bool = False
    validation_error_message: Optional[str] = None
    multiple_props: Optional[ComponentMultipleProps] = None


StateModel_co = TypeVar("StateModel_co", bound=PydanticBaseModel, covariant=True)
PropsModel_co = TypeVar("PropsModel_co", bound=PydanticBaseModel, covariant=True)


class Component(Generic[MN]):
    # TODO: Try typing this
    StateChangeHandler: TypeAlias = Callable[
        [StateModel_co, PropsModel_co], Awaitable[PydanticBaseModel]
    ]

    _handle_state_change: Optional[StateChangeHandler] = None
    _fut: Future[Any]

    schema: MethodDef
    instance: ComponentInstance
    on_state_change: Optional[Callable[[], Awaitable[None]]] = None
    validator: Optional[IOPromiseValidator] = None

    def __init__(
        self,
        method_name: MN,
        label: str,
        initial_props: Optional[dict[str, Any]],
        handle_state_change: Optional[StateChangeHandler] = None,
        is_optional: bool = False,
        validator: Optional[IOPromiseValidator] = None,
    ):
        if initial_props is None:
            initial_props = {}

        self.schema = io_schema[method_name]
        self.instance = ComponentInstance(
            method_name=method_name,
            label=label,
            props=dict_keys_to_camel(dict_strip_none(initial_props)),
            state=None,
            is_stateful=handle_state_change is not None,
            is_optional=is_optional,
        )
        self._handle_state_change = handle_state_change
        self.validator = validator

        loop = asyncio.get_running_loop()
        self._fut = loop.create_future()

    async def handle_validation(self, return_value: Any) -> Optional[str]:
        if self.validator is not None:
            resp = self.validator(return_value)
            message = cast(
                Optional[str], await resp if inspect.isawaitable(resp) else resp
            )
            self.instance.validation_error_message = message
            return message

    def set_return_value(self, value: Any):
        return_schema = self.schema.returns
        if self.instance.is_multiple:
            return_schema = list[return_schema]
        if self.instance.is_optional:
            return_schema = Optional[return_schema]

        try:
            if value is None:
                if not self.instance.is_optional and self.schema.returns is not None:
                    raise ValueError("Received invalid None return value")
                parsed = None
            else:
                parsed = parse_obj_as(return_schema, dict_keys_to_snake(value))
            self._fut.set_result(parsed)
        except ValueError as err:
            print("Received invalid return value:", err, file=sys.stderr)
            self._fut.set_exception(err)

    async def set_state(self, value: Any):
        try:
            parsed = parse_obj_as(self.schema.state, dict_keys_to_snake(value))
            if self._handle_state_change:
                self.instance.props = dict_keys_to_camel(
                    (
                        await self._handle_state_change(
                            parsed,
                            parse_obj_as(
                                self.schema.props,
                                dict_keys_to_snake(self.instance.props),
                            ),
                        )
                    ).dict()
                )
            elif parsed is not None:
                print(
                    "Received state, but no method was defined to handle.",
                    file=sys.stderr,
                )

            if self.on_state_change is not None:
                # This is definitely callable?
                # pylint: disable-next=not-callable
                await self.on_state_change()
        except ValidationError as err:
            print("Received invalid state:", value, err, file=sys.stderr)

    def set_optional(self, optional: bool):
        self.instance.is_optional = optional

    def set_multiple(self, multiple: bool):
        self.instance.is_multiple = multiple

    @property
    def return_value(self) -> Future[Any]:
        return self._fut

    @property
    def render_info(self):
        return ComponentRenderInfo(
            method_name=self.instance.method_name,
            label=self.instance.label,
            props=dict_keys_to_camel(self.instance.props),
            is_stateful=self.instance.is_stateful,
            is_optional=self.instance.is_optional,
            is_multiple=self.instance.is_multiple,
            validation_error_message=self.instance.validation_error_message,
            multiple_props=self.instance.multiple_props,
        )


ComponentRenderer: TypeAlias = Callable[
    [list[Component], Optional[IOPromiseValidator], Optional[ButtonConfig]],
    Awaitable[list[Any]],
]
