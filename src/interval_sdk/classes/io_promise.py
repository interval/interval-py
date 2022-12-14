from typing import (
    Generic,
    TypeVar,
    Callable,
    Any,
    Generator,
)

from .component import Component, ComponentRenderer
from ..io_schema import MethodName

Output = TypeVar("Output", covariant=True)

MN = TypeVar("MN", bound=MethodName, covariant=True)


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
