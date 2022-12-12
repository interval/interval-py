import asyncio, sys
from asyncio.futures import Future
from typing import (
    Any,
    Callable,
    Generator,
    Generic,
    TypeVar,
    TypeAlias,
    Awaitable,
    Literal,
    Mapping,
)


from pydantic import parse_obj_as, parse_raw_as, ValidationError

from .io_schema import (
    TableRowValue,
    MethodDef,
    MethodName,
    io_schema,
    ComponentRenderInfo,
)
from .types import GenericModel
from .util import dict_strip_none, dict_keys_to_camel

MN = TypeVar("MN", bound=MethodName, covariant=True)


class ComponentInstance(GenericModel, Generic[MN]):
    method_name: MN
    label: str
    # TODO: Try typing these
    props: dict[str, Any] = {}
    state: dict[str, Any] | None = None
    is_stateful: bool = False
    is_optional: bool = False


class Component(Generic[MN]):
    # TODO: Try typing this
    StateChangeHandler: TypeAlias = Callable[[Any], Awaitable[Any]]

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
            is_stateful=True if handle_state_change is not None else False,
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
                parsed = parse_obj_as(return_schema, value)
            self._fut.set_result(parsed)
        except ValueError as err:
            print("Received invalid return value:", err, file=sys.stderr)
            self._fut.set_exception(err)

    async def set_state(self, value: Any):
        state_schema = self.schema.state

        try:
            parsed = parse_raw_as(state_schema, value)
            if self._handle_state_change:
                self.instance.props.update(await self._handle_state_change(parsed))
            elif parsed is not None:
                print(
                    "Received state, but no method was defined to handle.",
                    file=sys.stderr,
                )

            if self.on_state_change:
                await self.on_state_change()
        except ValidationError as err:
            print("Received invalid state:", err, file=sys.stderr)

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


ComponentRenderer: TypeAlias = Callable[[list[Component]], Awaitable[list[Any]]]

Output = TypeVar("Output")


class BaseIOPromise(Generic[MN, Output]):
    component: Component
    renderer: ComponentRenderer
    get_value: Callable[[Any], Output] | None = None

    def __init__(
        self,
        component: Component,
        renderer: ComponentRenderer,
        get_value: Callable[[Any], Output] | None = None,
    ):
        self.component = component
        self.renderer = renderer
        self.get_value = get_value

    def __await__(self) -> Generator[Any, None, Output]:
        res = yield from self.renderer([self.component]).__await__()
        return self._get_value(res[0])

    def _get_value(self, val: Any) -> Output:
        if self.get_value:
            return self.get_value(val)

        return val


class ExclusiveIOPromise(BaseIOPromise[MN, Output]):
    pass


class GroupableIOPromise(BaseIOPromise[MN, Output]):
    pass


class OptionalIOPromise(GroupableIOPromise[MN, Output]):
    def __init__(
        self,
        component: Component,
        renderer: ComponentRenderer,
        get_value: Callable[[Any], Output] | None = None,
    ):
        component.instance.is_optional = True
        super().__init__(component, renderer, get_value)

    def _get_value(self, val: Any) -> Output | None:
        if val is None:
            return None

        if self.get_value:
            return self.get_value(val)

        return val


class IOPromise(GroupableIOPromise[MN, Output]):
    def optional(self) -> OptionalIOPromise[MN, Output | None]:
        return OptionalIOPromise[MN, Output | None](
            self.component, self.renderer, self.get_value
        )


TR = TypeVar("TR", bound=Mapping[str, TableRowValue])