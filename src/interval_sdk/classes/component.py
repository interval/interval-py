import asyncio, sys, traceback
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

from interval_sdk import superjson

from ..io_schema import (
    ChoiceButtonConfig,
    ChoiceReturn,
    ComponentMultipleProps,
    MethodDef,
    MN,
    io_schema,
    ComponentRenderInfo,
    resolves_immediately,
)
from ..types import GenericModel
from ..util import dict_keys_to_snake, dict_keys_to_camel

Output_co = TypeVar("Output_co", covariant=True)
GroupOutput = TypeVarTuple("GroupOutput")

IOPromiseValidator: TypeAlias = Callable[
    [Output_co], Union[Awaitable[Optional[str]], str, None]
]
IOGroupPromiseValidator: TypeAlias = Callable[
    [Unpack[GroupOutput]], Union[Awaitable[Optional[str]], str, None]
]
WithChoicesIOGroupPromiseValidator: TypeAlias = Callable[
    [ChoiceReturn[Output_co]],
    Union[Awaitable[Optional[str]], str, None],
]

StateModel_co = TypeVar(
    "StateModel_co", bound=Union[PydanticBaseModel, None], covariant=True
)
PropsModel_co = TypeVar(
    "PropsModel_co", bound=Union[PydanticBaseModel, None], covariant=True
)


class ComponentInstance(GenericModel, Generic[MN, PropsModel_co, StateModel_co]):
    method_name: MN
    label: str
    props: PropsModel_co
    state: Optional[StateModel_co]
    is_stateful: bool = False
    is_optional: bool = False
    is_multiple: bool = False
    validation_error_message: Optional[str] = None
    multiple_props: Optional[ComponentMultipleProps] = None


class Component(Generic[MN, PropsModel_co, StateModel_co]):
    _handle_state_change: Optional[
        Callable[[StateModel_co, PropsModel_co], Awaitable[PropsModel_co]]
    ] = None
    _fut: Future[Any]

    schema: MethodDef
    instance: ComponentInstance[MN, PropsModel_co, StateModel_co]
    on_state_change: Optional[Callable[[], Awaitable[None]]] = None
    validator: Optional[IOPromiseValidator] = None
    resolves_immediately: bool = False

    def __init__(
        self,
        method_name: MN,
        label: str,
        initial_props: PropsModel_co,
        handle_state_change: Optional[
            Callable[[StateModel_co, PropsModel_co], Awaitable[PropsModel_co]]
        ] = None,
        is_optional: bool = False,
        validator: Optional[IOPromiseValidator] = None,
        *,
        display_resolves_immediately: Optional[bool] = None,
    ):
        self.schema = io_schema[method_name]
        self.instance = ComponentInstance[MN, PropsModel_co, StateModel_co](
            method_name=method_name,
            label=label,
            props=initial_props,
            state=None,
            is_stateful=handle_state_change is not None,
            is_optional=is_optional,
        )
        self._handle_state_change = handle_state_change
        self.validator = validator

        loop = asyncio.get_running_loop()
        self._fut = loop.create_future()
        self.resolves_immediately = resolves_immediately(
            method_name, display_resolves_immediately=display_resolves_immediately
        )

    async def handle_validation(self, return_value: Any) -> Optional[str]:
        try:
            parsed = self.parse_return_value(return_value)
            if self.validator is not None:
                resp = self.validator(parsed)
                message = cast(
                    Optional[str], await resp if inspect.isawaitable(resp) else resp
                )
                self.instance.validation_error_message = message
                return message
            else:
                return None
        except BaseException as err:
            print(
                f"[Interval] Received invalid return value ({return_value}):",
                err,
                file=sys.stderr,
            )
            traceback.print_exc(file=sys.stderr)
            return "Received invalid response."

    def set_return_value(self, value: Any):
        if self._fut.done():
            return

        try:
            parsed = self.parse_return_value(value)
            self._fut.set_result(parsed)
        except BaseException as err:
            print(
                f"[Interval] Received invalid return value ({value}):",
                err,
                file=sys.stderr,
            )
            traceback.print_exc(file=sys.stderr)
            self._fut.set_exception(err)

    def set_exception(self, err: BaseException):
        if self._fut.done():
            return

        self._fut.set_exception(err)

    async def set_state(self, value: Any):
        try:
            parsed = parse_obj_as(self.schema.state, dict_keys_to_snake(value))
            if self._handle_state_change:
                await self.set_props(
                    await self._handle_state_change(
                        parsed,
                        parse_obj_as(
                            self.schema.props,
                            dict_keys_to_snake(self.instance.props),
                        ),
                    )
                )
            elif parsed is not None:
                print(
                    "[Interval] Received state, but no method was defined to handle.",
                    file=sys.stderr,
                )

        except ValidationError as err:
            print("[Interval] Received invalid state:", value, err, file=sys.stderr)

    async def set_props(self, value: Any):
        self.instance.props = value

        if self.on_state_change is not None:
            # This is definitely callable?
            # pylint: disable-next=not-callable
            await self.on_state_change()

    def parse_return_value(self, value: Any):
        return_schema = self.schema.returns
        if self.instance.is_multiple:
            return_schema = list[return_schema]
        if self.instance.is_optional:
            return_schema = Optional[return_schema]

        if value is None:
            if not self.instance.is_optional and self.schema.returns is not None:
                raise ValueError("Received invalid None return value")
            return None

        return parse_obj_as(return_schema, dict_keys_to_snake(value))

    def set_optional(self, optional: bool):
        self.instance.is_optional = optional

    def set_multiple(self, multiple: bool):
        self.instance.is_multiple = multiple

    @property
    def return_value(self) -> Future[Any]:
        return self._fut

    @property
    def render_info(self):
        props, meta = superjson.serialize(
            dict_keys_to_camel(self.instance.props.dict(exclude_defaults=True))
            if self.instance.props is not None
            else {}
        )
        return ComponentRenderInfo(
            method_name=self.instance.method_name,
            label=self.instance.label,
            props=props,
            props_meta=meta,
            is_stateful=self.instance.is_stateful,
            is_optional=self.instance.is_optional,
            is_multiple=self.instance.is_multiple,
            validation_error_message=self.instance.validation_error_message,
            multiple_props=self.instance.multiple_props,
        )


ComponentRenderer: TypeAlias = Callable[
    [
        list[Component],
        Optional[WithChoicesIOGroupPromiseValidator[list[Any]]],
        Optional[list[ChoiceButtonConfig]],
    ],
    Awaitable[tuple[list[Any], Optional[str]]],
]
