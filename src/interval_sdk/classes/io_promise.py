from typing import (
    Generic,
    TypeVar,
    Callable,
    Any,
    Generator,
)
from typing_extensions import override

from .component import Component, ComponentRenderer
from ..io_schema import MethodName

Output_co = TypeVar("Output_co", covariant=True)

MN_co = TypeVar("MN_co", bound=MethodName, covariant=True)


class BaseIOPromise(Generic[MN_co, Output_co]):
    _component: Component
    _renderer: ComponentRenderer
    _value_getter: Callable[[Any], Output_co] | None = None

    def __init__(
        self,
        component: Component,
        renderer: ComponentRenderer,
        get_value: Callable[[Any], Output_co] | None = None,
    ):
        self._component = component
        self._renderer = renderer
        self._value_getter = get_value

    def __await__(self) -> Generator[Any, None, Output_co]:
        res = yield from self._renderer([self._component]).__await__()
        return self._get_value(res[0])

    def _get_value(self, val: Any) -> Output_co:
        if self._value_getter is not None:
            return self._value_getter(val)

        return val


class ExclusiveIOPromise(BaseIOPromise[MN_co, Output_co]):
    pass


class GroupableIOPromise(BaseIOPromise[MN_co, Output_co]):
    pass


class OptionalIOPromise(GroupableIOPromise[MN_co, Output_co]):
    def __init__(
        self,
        component: Component,
        renderer: ComponentRenderer,
        get_value: Callable[[Any], Output_co] | None = None,
    ):
        component.instance.is_optional = True
        super().__init__(component, renderer, get_value)

    @override
    def __await__(self) -> Generator[Any, None, Output_co | None]:
        res = yield from self._renderer([self._component]).__await__()
        if res[0] is None:
            return None
        return self._get_value(res[0])


class IOPromise(GroupableIOPromise[MN_co, Output_co]):
    def optional(self) -> OptionalIOPromise[MN_co, Output_co | None]:
        return OptionalIOPromise[MN_co, Output_co | None](
            self._component, self._renderer, self._value_getter
        )
