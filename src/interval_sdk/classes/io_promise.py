import inspect, sys
from typing import (
    Awaitable,
    Generic,
    Iterable,
    Literal,
    TypeVar,
    Callable,
    Any,
    Generator,
    cast,
    overload,
)
from typing_extensions import Unpack, override

from pydantic import ValidationError, parse_obj_as

from interval_sdk.types import BaseModel

from .component import (
    Component,
    ComponentRenderer,
    GroupOutput,
    IOGroupPromiseValidator,
    Output_co,
    IOPromiseValidator,
)
from ..io_schema import (
    ComponentMultipleProps,
    input_schema,
    ButtonConfig,
    DisplayMethodName,
    InputMethodName,
    MethodName,
    MultipleableMethodName,
)

MN_co = TypeVar("MN_co", bound=MethodName, covariant=True)
Display_MN_co = TypeVar("Display_MN_co", bound=DisplayMethodName, covariant=True)
Input_MN_co = TypeVar("Input_MN_co", bound=InputMethodName, covariant=True)
Multipleable_MN_co = TypeVar(
    "Multipleable_MN_co", bound=MultipleableMethodName, covariant=True
)


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
        res = yield from self._renderer([self._component], None, None).__await__()
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


InputIOPromiseSelf = TypeVar("InputIOPromiseSelf", bound="InputIOPromise")


class InputIOPromise(GroupableIOPromise[Input_MN_co, Output_co]):
    def optional(self) -> "OptionalIOPromise[Input_MN_co, Output_co | None]":
        return OptionalIOPromise[Input_MN_co, Output_co | None](
            self._component,
            self._renderer,
            self._value_getter,
        )

    def validate(
        self: InputIOPromiseSelf, validator: IOPromiseValidator[Output_co] | None
    ) -> InputIOPromiseSelf:
        if validator is None:
            self._component.validator = None
        else:
            if self._value_getter is not None:

                async def handle_validation(return_value: Any) -> str | None:
                    ret = validator(self._get_value(return_value))
                    if inspect.isawaitable(ret):
                        return await ret

                    return cast(str | None, ret)

                self._component.validator = handle_validation
            else:
                self._component.validator = validator

        return self


class OptionalIOPromise(InputIOPromise[Input_MN_co, Output_co]):
    def __init__(
        self,
        component: Component,
        renderer: ComponentRenderer,
        get_value: Callable[[Any], Output_co] | None = None,
    ):
        component.instance.is_optional = True
        component.validator = None
        super().__init__(
            component=component,
            renderer=renderer,
            get_value=get_value,
        )

    @override
    def __await__(self) -> Generator[Any, None, Output_co | None]:
        res = yield from self._renderer([self._component], None, None).__await__()
        return self._get_value(res[0])

    def _get_value(self, val: Any) -> Output_co | None:
        if val is None:
            return None

        return super()._get_value(val)


DefaultValue = TypeVar("DefaultValue")


class MultipleableIOPromise(
    Generic[Multipleable_MN_co, Output_co, DefaultValue],
    InputIOPromise[Multipleable_MN_co, Output_co],
):
    _default_value_getter: Callable[[Any], Any] | None = None

    def __init__(
        self,
        component: Component,
        renderer: ComponentRenderer,
        get_value: Callable[[Any], Output_co] | None = None,
        get_default_value: Callable[[Any], Any] | None = None,
    ):
        self._default_value_getter = get_default_value
        super().__init__(
            component=component,
            renderer=renderer,
            get_value=get_value,
        )

    def multiple(self, *, default_value: Iterable[DefaultValue] | None = None):
        transformed_default_value = None
        if default_value is not None:
            potential_default_value = (
                [self._default_value_getter(i) for i in default_value]
                if self._default_value_getter is not None
                else default_value
            )
            try:
                props_schema: BaseModel = input_schema[
                    self._component.instance.method_name
                ].props
                default_value_field = props_schema.__fields__["defaultValue"]
                transformed_default_value = parse_obj_as(
                    list[default_value_field.type_], potential_default_value
                )
            except ValidationError as e:
                print(
                    f"[Interval] Invalid default value found for multiple IO call with label {self._component.instance.label}: {default_value}. This default value will be ignored.",
                    file=sys.stderr,
                )
                print(e, file=sys.stderr)
                transformed_default_value = None

        return MultipleIOPromise(
            component=self._component,
            renderer=self._renderer,
            get_value=self._value_getter,
            default_value=transformed_default_value,
        )


MultipleIOPromiseSelf = TypeVar("MultipleIOPromiseSelf", bound="MultipleIOPromise")


class MultipleIOPromise(
    Generic[Multipleable_MN_co, Output_co, DefaultValue],
    InputIOPromise[Multipleable_MN_co, Iterable[Output_co]],
):
    _single_value_getter: Callable[[Any], Output_co] | None = None

    def __init__(
        self,
        component: Component,
        renderer: ComponentRenderer,
        get_value: Callable[[Any], Output_co] | None = None,
        default_value: list[Any] | None = None,
    ):
        self._single_value_getter = get_value
        value_getter = None
        if get_value is not None:
            getter = get_value

            def multiple_value_getter(return_values: Iterable[Any]) -> list[Output_co]:
                return [getter(v) for v in return_values]

            value_getter = multiple_value_getter

        component.set_multiple(True)
        component.validator = None
        if default_value is not None:
            component.instance.multiple_props = ComponentMultipleProps(
                default_value=default_value
            )
        super().__init__(
            component=component,
            renderer=renderer,
            get_value=value_getter,
        )

    @override
    def __await__(self) -> Generator[Any, None, list[Output_co]]:
        res = yield from self._renderer([self._component], None, None).__await__()
        return self._get_value(res[0])

    def _get_value(self, val: list[Any]) -> list[Output_co]:
        if self._single_value_getter is not None:
            return [self._single_value_getter(v) for v in val]

        return cast(list[Output_co], val)

    def validate(
        self: MultipleIOPromiseSelf,
        validator: IOPromiseValidator[Iterable[Output_co]] | None,
    ) -> MultipleIOPromiseSelf:
        if validator is None:
            self._component.validator = None
        else:
            if self._value_getter is not None:
                value_getter = self._value_getter

                async def handle_validation(return_values: Iterable[Any]) -> str | None:
                    ret = validator(value_getter(return_values))
                    if inspect.isawaitable(ret):
                        return await ret

                    return cast(str | None, ret)

                self._component.validator = handle_validation
            else:
                self._component.validator = validator

        return self

    def optional(
        self,
    ) -> OptionalIOPromise[Multipleable_MN_co, Iterable[Output_co] | None]:
        return OptionalIOPromise[Multipleable_MN_co, Iterable[Output_co] | None](
            component=self._component,
            renderer=self._renderer,
            get_value=self._value_getter,
        )


IOGroupPromiseSelf = TypeVar("IOGroupPromiseSelf", bound="IOGroupPromise")


class KeyedIONamespace:
    __items: dict[str, Any] = {}

    def __init__(self, items: dict[str, Any]):
        self.__items = items

    def __getattr__(self, name: str) -> Any:
        return self.__items[name]


class IOGroupPromise(Generic[Unpack[GroupOutput]]):
    _io_promises: tuple[GroupableIOPromise[MethodName, Any], ...]
    _kw_io_promises: dict[str, GroupableIOPromise[MethodName, Any]] | None = None
    _renderer: ComponentRenderer
    _validator: "IOGroupPromiseValidator[Unpack[GroupOutput]] | None" = None
    _continue_button: ButtonConfig | None = None

    def __init__(
        self,
        renderer: ComponentRenderer,
        io_promises: tuple[GroupableIOPromise[MethodName, Any], ...],
        kw_io_promises: dict[str, GroupableIOPromise[MethodName, Any]] | None = None,
    ):
        self._renderer = renderer
        self._io_promises = io_promises
        self._kw_io_promises = kw_io_promises

    @overload
    def __await__(
        self: "IOGroupPromise[KeyedIONamespace]",
    ) -> Generator[Any, None, KeyedIONamespace]:
        """Fallback typing for calls with keyword arguments."""
        ...

    @overload
    def __await__(self: "IOGroupPromise[list[Any]]") -> Generator[Any, None, list[Any]]:
        """Fallback typing for calls with 10 or more arguments."""
        ...

    @overload
    def __await__(self) -> Generator[Any, None, tuple[Unpack[GroupOutput]]]:
        ...

    def __await__(self) -> Generator[Any, None, tuple[Unpack[GroupOutput]] | KeyedIONamespace]:  # type: ignore
        if self._kw_io_promises is not None and len(self._kw_io_promises) > 0:
            res = yield from self._renderer(
                [p._component for p in self._kw_io_promises.values()],
                self._handle_validation,
                self._continue_button,
            ).__await__()
            res_dict = {
                key: res[i] for i, key in enumerate(self._kw_io_promises.keys())
            }
            return KeyedIONamespace(res_dict)
        else:
            res = yield from self._renderer(
                [p._component for p in self._io_promises],
                self._handle_validation,
                self._continue_button,
            ).__await__()
            return cast(
                tuple[Unpack[GroupOutput]],
                [self._io_promises[i]._get_value(val) for (i, val) in enumerate(res)],
            )

    async def _handle_validation(self, return_values: list[Any]) -> str | None:
        if self._validator is None:
            return None

        if self._kw_io_promises is not None and len(self._kw_io_promises) > 0:
            io_promises = list(self._kw_io_promises.values())
            values = {
                key: io_promises[index]._get_value(return_values[index])
                for index, key in enumerate(self._kw_io_promises.keys())
            }
            ret = self._validator(**values)  # type: ignore
        else:
            io_promises = self._io_promises
            values = [
                io_promises[index]._get_value(v)
                for index, v in enumerate(return_values)
            ]
            ret = self._validator(*values)  # type: ignore
        return cast(str | None, await ret if inspect.isawaitable(ret) else ret)

    @overload
    def validate(
        self: "IOGroupPromise[KeyedIONamespace]",
        validator: "Callable[..., str | None | Awaitable[str | None]] | None",
    ) -> "IOGroupPromise[Unpack[GroupOutput]]":
        ...

    @overload
    def validate(
        self: "IOGroupPromise[Unpack[GroupOutput]]",
        validator: "IOGroupPromiseValidator[Unpack[GroupOutput]] | None",
    ) -> "IOGroupPromise[Unpack[GroupOutput]]":
        ...

    def validate(  # type: ignore
        self: "IOGroupPromise[Unpack[GroupOutput]]",
        validator: "IOGroupPromiseValidator[Unpack[GroupOutput]] | None",
    ) -> "IOGroupPromise[Unpack[GroupOutput]]":
        self._validator = validator
        return self

    def continue_button_options(
        self: "IOGroupPromise[Unpack[GroupOutput]]",
        label: str | None = None,
        theme: Literal["primary", "secondary", "danger"] | None = None,
    ) -> "IOGroupPromise[Unpack[GroupOutput]]":
        self._continue_button = ButtonConfig(label=label, theme=theme)
        return self
