import asyncio, sys
from asyncio.futures import Future
from typing import (
    Any,
    Callable,
    Generic,
    TypeAlias,
    Awaitable,
    TypeVar,
)


from pydantic import parse_obj_as, ValidationError, BaseModel as PydanticBaseModel

from ..io_schema import (
    MethodDef,
    MN,
    io_schema,
    ComponentRenderInfo,
)
from ..types import GenericModel
from ..util import dict_keys_to_snake, dict_strip_none, dict_keys_to_camel


class ComponentInstance(GenericModel, Generic[MN]):
    method_name: MN
    label: str
    # TODO: Try typing these
    props: dict[str, Any] = {}
    state: dict[str, Any] | None = None
    is_stateful: bool = False
    is_optional: bool = False


StateModel_co = TypeVar("StateModel_co", bound=PydanticBaseModel, covariant=True)
PropsModel_co = TypeVar("PropsModel_co", bound=PydanticBaseModel, covariant=True)


class Component(Generic[MN]):
    # TODO: Try typing this
    StateChangeHandler: TypeAlias = Callable[
        [StateModel_co, PropsModel_co], Awaitable[PydanticBaseModel]
    ]

    _handle_state_change: StateChangeHandler | None = None
    _fut: Future[Any]

    schema: MethodDef
    instance: ComponentInstance
    on_state_change: Callable[[], Awaitable[None]] | None = None

    def __init__(
        self,
        method_name: MN,
        label: str,
        initial_props: dict[str, Any] | None,
        handle_state_change: StateChangeHandler | None = None,
        is_optional: bool = False,
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

        loop = asyncio.get_running_loop()
        self._fut = loop.create_future()

    def set_return_value(self, value: Any):
        return_schema = self.schema.returns
        if self.instance.is_optional:
            return_schema = return_schema | None

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
        )


Output_co = TypeVar("Output_co", covariant=True)

IOPromiseValidator: TypeAlias = Callable[[Output_co], Awaitable[str | None]]
ComponentRenderer: TypeAlias = Callable[
    [list[Component], IOPromiseValidator | None], Awaitable[list[Any]]
]
