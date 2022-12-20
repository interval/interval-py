from typing import (
    Generic,
    TypeVar,
    Callable,
    Any,
    Generator,
    cast,
)
from typing_extensions import override

from .component import Component, ComponentRenderer, Output_co, IOPromiseValidator
from ..io_schema import DisplayMethodName, InputMethodName, MethodName

MN_co = TypeVar("MN_co", bound=MethodName, covariant=True)
Display_MN_co = TypeVar("Display_MN_co", bound=DisplayMethodName, covariant=True)
Input_MN_co = TypeVar("Input_MN_co", bound=InputMethodName, covariant=True)


class IOPromise(Generic[MN_co, Output_co]):
    _component: Component
    _renderer: ComponentRenderer
    _value_getter: Callable[[Any], Output_co] | None = None
    _validator: IOPromiseValidator[Output_co] | None = None

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
        res = yield from self._renderer([self._component], self._validator).__await__()
        return self._get_value(res[0])

    def _get_value(self, val: Any) -> Output_co:
        if self._value_getter is not None:
            return self._value_getter(val)

        return val


class ExclusiveIOPromise(IOPromise[MN_co, Output_co]):
    pass


class GroupableIOPromise(IOPromise[MN_co, Output_co]):
    pass


class DisplayIOPromise(GroupableIOPromise[Display_MN_co, Output_co]):
    pass


class InputIOPromise(GroupableIOPromise[Input_MN_co, Output_co]):
    def optional(self) -> "OptionalIOPromise[Input_MN_co, Output_co | None]":
        return OptionalIOPromise[Input_MN_co, Output_co | None](
            self._component, self._renderer, self._value_getter
        )


class OptionalIOPromise(InputIOPromise[Input_MN_co, Output_co]):
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
        res = yield from self._renderer([self._component], self._validator).__await__()
        return self._get_value(res[0])

    def _get_value(self, val: Any) -> Output_co | None:
        if val is None:
            return None

        return super()._get_value(val)


IOGroupPromiseSelf = TypeVar("IOGroupPromiseSelf", bound="IOGroupPromise")


class IOGroupPromise(Generic[Output_co]):
    _io_promises: tuple[GroupableIOPromise[MethodName, Any], ...]
    _renderer: ComponentRenderer
    _validator: IOPromiseValidator[Output_co] | None = None

    def __init__(
        self,
        io_promises: tuple[GroupableIOPromise[MethodName, Any], ...],
        renderer: ComponentRenderer,
    ):
        self._io_promises = io_promises
        self._renderer = renderer

    def __await__(self) -> Generator[Any, None, Output_co]:
        res = yield from self._renderer(
            [p._component for p in self._io_promises], self._validator
        ).__await__()
        return cast(
            Output_co,
            [self._io_promises[i]._get_value(val) for (i, val) in enumerate(res)],
        )

    def validate(
        self: IOGroupPromiseSelf, validator: IOPromiseValidator[Output_co] | None
    ) -> IOGroupPromiseSelf:
        self._validator = validator
        return self

    async def _handle_validation(self, return_values: list[Any]) -> str | None:
        if self._validator is None:
            return None

        io_promises = self._io_promises
        values = [
            io_promises[index]._get_value(v) for index, v in enumerate(return_values)
        ]
        return await self._validator(cast(Output_co, values))
