import inspect, sys
from typing import (
    Awaitable,
    Generic,
    Iterable,
    Iterator,
    Literal,
    Mapping,
    Optional,
    TypeVar,
    Callable,
    Any,
    Generator,
    Union,
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
    WithChoicesIOGroupPromiseValidator,
)
from ..io_schema import (
    ButtonTheme,
    ComponentMultipleProps,
    input_schema,
    ChoiceReturn,
    ChoiceButton,
    ChoiceButtonConfig,
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
    _value_getter: Optional[Callable[[Any], Output_co]] = None
    _validator: Optional[IOPromiseValidator[Output_co]] = None

    def __init__(
        self,
        component: Component,
        renderer: ComponentRenderer,
        get_value: Optional[Callable[[Any], Output_co]] = None,
    ):
        self._component = component
        self._renderer = renderer
        self._value_getter = get_value

    def __await__(self) -> Generator[Any, None, Output_co]:
        return_values, _choice = yield from self._renderer(
            [self._component],
            None,
            None,
        ).__await__()
        return self._get_value(return_values[0])

    def _get_value(self, val: Any) -> Output_co:
        if self._value_getter is not None:
            return self._value_getter(val)

        return val

    def with_choices(
        self,
        choices: Iterable[Union[ChoiceButton, str]],
    ) -> "WithChoicesIOPromise[MN_co, Output_co]":
        return WithChoicesIOPromise[MN_co, Output_co](
            self._component,
            self._renderer,
            choices=[
                ChoiceButtonConfig.parse_obj(
                    {"label": item, "value": item} if isinstance(item, str) else item
                )
                for item in choices
            ],
            get_value=self._value_getter,
        )


class ExclusiveIOPromise(IOPromise[MN_co, Output_co]):
    pass


class GroupableIOPromise(IOPromise[MN_co, Output_co]):
    pass


class DisplayIOPromise(GroupableIOPromise[Display_MN_co, Output_co]):
    pass


InputIOPromiseSelf = TypeVar("InputIOPromiseSelf", bound="InputIOPromise")


class InputIOPromise(GroupableIOPromise[Input_MN_co, Output_co]):
    @overload
    def optional(
        self,
        optional: Literal[True] = True,
    ) -> "OptionalIOPromise[Input_MN_co, Optional[Output_co]]":
        ...

    @overload
    def optional(
        self: InputIOPromiseSelf,
        optional: Literal[False],
    ) -> InputIOPromiseSelf:
        ...

    @overload
    def optional(
        self: InputIOPromiseSelf,
        optional: bool,
    ) -> "Union[OptionalIOPromise[Input_MN_co, Optional[Output_co]], InputIOPromiseSelf]":
        ...

    def optional(
        self: InputIOPromiseSelf,
        optional: bool = True,
    ) -> "Union[OptionalIOPromise[Input_MN_co, Optional[Output_co]], InputIOPromiseSelf]":
        return (
            OptionalIOPromise[Input_MN_co, Optional[Output_co]](
                self._component,
                self._renderer,
                self._value_getter,
            )
            if optional
            else self
        )

    def validate(
        self: InputIOPromiseSelf, validator: Optional[IOPromiseValidator[Output_co]]
    ) -> InputIOPromiseSelf:
        if validator is None:
            self._component.validator = None
        else:
            if self._value_getter is not None:

                async def handle_validation(return_value: Any) -> Optional[str]:
                    ret = validator(self._get_value(return_value))
                    if inspect.isawaitable(ret):
                        return await ret

                    return cast(Optional[str], ret)

                self._component.validator = handle_validation
            else:
                self._component.validator = validator

        return self

    def with_choices(
        self,
        choices: Iterable[Union[ChoiceButton, str]],
    ) -> "WithChoicesInputIOPromise[Input_MN_co, Output_co]":
        return WithChoicesInputIOPromise[Input_MN_co, Output_co](
            self._component,
            self._renderer,
            choices=[
                ChoiceButtonConfig.parse_obj(
                    {"label": item, "value": item} if isinstance(item, str) else item
                )
                for item in choices
            ],
            get_value=self._value_getter,
        )


class OptionalIOPromise(InputIOPromise[Input_MN_co, Output_co]):
    def __init__(
        self,
        component: Component,
        renderer: ComponentRenderer,
        get_value: Optional[Callable[[Any], Output_co]] = None,
    ):
        component.instance.is_optional = True
        component.validator = None
        super().__init__(
            component=component,
            renderer=renderer,
            get_value=get_value,
        )

    @override
    def __await__(self) -> Generator[Any, None, Optional[Output_co]]:
        return_values, _choice = yield from self._renderer(
            [self._component], None, None
        ).__await__()
        return self._get_value(return_values[0])

    def _get_value(self, val: Any) -> Optional[Output_co]:
        if val is None:
            return None

        return super()._get_value(val)

    def with_choices(
        self,
        choices: Iterable[Union[ChoiceButton, str]],
    ) -> "WithChoicesOptionalIOPromise[Input_MN_co, Output_co]":
        return WithChoicesOptionalIOPromise[Input_MN_co, Output_co](
            self._component,
            self._renderer,
            choices=[
                ChoiceButtonConfig.parse_obj(
                    {"label": item, "value": item} if isinstance(item, str) else item
                )
                for item in choices
            ],
            get_value=self._value_getter,
        )


WithChoicesOptionalIOPromiseSelf = TypeVar(
    "WithChoicesOptionalIOPromiseSelf", bound="WithChoicesOptionalIOPromise"
)


class WithChoicesOptionalIOPromise(OptionalIOPromise[Input_MN_co, Output_co]):
    _choice_buttons: list[ChoiceButtonConfig]
    _validator: Optional[WithChoicesIOGroupPromiseValidator[Optional[Output_co]]]

    def __init__(
        self,
        component: Component,
        renderer: ComponentRenderer,
        choices: list[ChoiceButtonConfig],
        get_value: Optional[Callable[[Any], Output_co]] = None,
    ):
        component.instance.is_optional = True
        component.validator = None
        super().__init__(
            component=component,
            renderer=renderer,
            get_value=get_value,
        )
        self._choice_buttons = choices

    @override
    def __await__(self) -> Generator[Any, None, ChoiceReturn[Optional[Output_co]]]:
        return_values, choice = yield from self._renderer(
            [self._component], self._handle_validation, self._choice_buttons
        ).__await__()
        return ChoiceReturn(
            choice=cast(str, choice),
            return_value=self._get_value(return_values[0]),
        )

    def _get_value(self, val: Any) -> Optional[Output_co]:
        if val is None:
            return None

        return super()._get_value(val)

    def with_choices(
        self,
        choices: Iterable[Union[ChoiceButton, str]],
    ) -> "WithChoicesOptionalIOPromise[Input_MN_co, Output_co]":
        self._choice_buttons = [
            ChoiceButtonConfig.parse_obj(
                {"label": item, "value": item} if isinstance(item, str) else item
            )
            for item in choices
        ]
        return self

    @override
    def validate(
        self: WithChoicesOptionalIOPromiseSelf,
        validator: Optional[WithChoicesIOGroupPromiseValidator[Optional[Output_co]]],
    ) -> WithChoicesOptionalIOPromiseSelf:
        self._component.validator = None
        self._validator = validator
        return self

    async def _handle_validation(self, ret: ChoiceReturn[list[Any]]):
        if self._validator is None:
            return None

        value = (
            self._get_value(ret.return_value[0])
            if self._value_getter is not None
            else ret.return_value[0]
        )

        validate_ret = self._validator(
            ChoiceReturn(choice=ret.choice, return_value=value)
        )

        return cast(
            Optional[str],
            await validate_ret if inspect.isawaitable(validate_ret) else validate_ret,
        )


DefaultValue = TypeVar("DefaultValue")


class MultipleableIOPromise(
    Generic[Multipleable_MN_co, Output_co, DefaultValue],
    InputIOPromise[Multipleable_MN_co, Output_co],
):
    _default_value_getter: Optional[Callable[[Any], Any]] = None

    def __init__(
        self,
        component: Component,
        renderer: ComponentRenderer,
        get_value: Optional[Callable[[Any], Output_co]] = None,
        get_default_value: Optional[Callable[[Any], Any]] = None,
    ):
        self._default_value_getter = get_default_value
        super().__init__(
            component=component,
            renderer=renderer,
            get_value=get_value,
        )

    def multiple(self, *, default_value: Optional[Iterable[DefaultValue]] = None):
        transformed_default_value = None
        if default_value is not None:
            potential_default_value = (
                [self._default_value_getter(i) for i in default_value]
                if self._default_value_getter is not None
                else list(default_value)
            )
            if len(potential_default_value) > 0:
                try:
                    props_schema: BaseModel = input_schema[
                        self._component.instance.method_name
                    ].props
                    default_value_field = props_schema.__fields__["default_value"]
                    transformed_default_value = parse_obj_as(
                        list[default_value_field.type_], potential_default_value
                    )
                except (ValidationError, KeyError) as e:
                    print(
                        f"[Interval] Invalid default value found for multiple IO call with label {self._component.instance.label}: {default_value}. This default value will be ignored.",
                        file=sys.stderr,
                    )
                    if isinstance(e, ValidationError):
                        print(e, file=sys.stderr)
                        transformed_default_value = None

        return MultipleIOPromise(
            component=self._component,
            renderer=self._renderer,
            get_value=self._value_getter,
            default_value=transformed_default_value,
        )

    def with_choices(
        self,
        choices: Iterable[Union[ChoiceButton, str]],
    ) -> "WithChoicesMultipleableIOPromise[Multipleable_MN_co, Output_co, DefaultValue]":
        return WithChoicesMultipleableIOPromise[
            Multipleable_MN_co, Output_co, DefaultValue
        ](
            self._component,
            self._renderer,
            choices=[
                ChoiceButtonConfig.parse_obj(
                    {"label": item, "value": item} if isinstance(item, str) else item
                )
                for item in choices
            ],
            get_value=self._value_getter,
        )


MultipleIOPromiseSelf = TypeVar("MultipleIOPromiseSelf", bound="MultipleIOPromise")


class MultipleIOPromise(
    Generic[Multipleable_MN_co, Output_co, DefaultValue],
    InputIOPromise[Multipleable_MN_co, Iterable[Output_co]],
):
    _single_value_getter: Optional[Callable[[Any], Output_co]] = None

    def __init__(
        self,
        component: Component,
        renderer: ComponentRenderer,
        get_value: Optional[Callable[[Any], Output_co]] = None,
        default_value: Optional[list[Any]] = None,
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
                defaultValue=default_value
            )
        super().__init__(
            component=component,
            renderer=renderer,
            get_value=value_getter,
        )

    @override
    def __await__(self) -> Generator[Any, None, list[Output_co]]:
        return_values, _choice = yield from self._renderer(
            [self._component], None, None
        ).__await__()
        return self._get_value(return_values[0])

    def _get_value(self, val: list[Any]) -> list[Output_co]:
        if self._single_value_getter is not None:
            return [self._single_value_getter(v) for v in val]

        return cast(list[Output_co], val)

    def validate(
        self: MultipleIOPromiseSelf,
        validator: Optional[IOPromiseValidator[Iterable[Output_co]]],
    ) -> MultipleIOPromiseSelf:
        if validator is None:
            self._component.validator = None
        else:
            if self._value_getter is not None:
                value_getter = self._value_getter

                async def handle_validation(
                    return_values: Iterable[Any],
                ) -> Optional[str]:
                    ret = validator(value_getter(return_values))
                    if inspect.isawaitable(ret):
                        return await ret

                    return cast(Optional[str], ret)

                self._component.validator = handle_validation
            else:
                self._component.validator = validator

        return self

    @overload
    def optional(
        self,
        optional: Literal[True] = True,
    ) -> OptionalIOPromise[Multipleable_MN_co, Optional[Iterable[Output_co]]]:
        ...

    @overload
    def optional(
        self: MultipleIOPromiseSelf,
        optional: Literal[False],
    ) -> MultipleIOPromiseSelf:
        ...

    @overload
    def optional(
        self: MultipleIOPromiseSelf,
        optional: bool,
    ) -> Union[
        OptionalIOPromise[Multipleable_MN_co, Optional[Iterable[Output_co]]],
        MultipleIOPromiseSelf,
    ]:
        ...

    def optional(
        self: MultipleIOPromiseSelf,
        optional: bool = True,
    ) -> Union[
        OptionalIOPromise[Multipleable_MN_co, Optional[Iterable[Output_co]]],
        MultipleIOPromiseSelf,
    ]:
        return (
            OptionalIOPromise[Multipleable_MN_co, Optional[Iterable[Output_co]]](
                component=self._component,
                renderer=self._renderer,
                get_value=self._value_getter,
            )
            if optional
            else self
        )


class WithChoicesIOPromise(IOPromise[MN_co, Output_co]):
    _choice_buttons: list[ChoiceButtonConfig]

    def __init__(
        self,
        component: Component,
        renderer: ComponentRenderer,
        choices: list[ChoiceButtonConfig],
        get_value: Optional[Callable[[Any], Output_co]] = None,
    ):
        super().__init__(
            component=component,
            renderer=renderer,
            get_value=get_value,
        )
        self._choice_buttons = choices

    @override
    def __await__(self) -> Generator[Any, None, ChoiceReturn[Output_co]]:
        return_values, choice = yield from self._renderer(
            [self._component], None, self._choice_buttons
        ).__await__()
        return ChoiceReturn(
            choice=cast(str, choice),
            return_value=self._get_value(return_values[0]),
        )


WithChoicesInputIOPromiseSelf = TypeVar(
    "WithChoicesInputIOPromiseSelf", bound="WithChoicesInputIOPromise"
)


class WithChoicesInputIOPromise(InputIOPromise[Input_MN_co, Output_co]):
    _choice_buttons: list[ChoiceButtonConfig]
    _validator: Optional[WithChoicesIOGroupPromiseValidator[Output_co]] = None

    def __init__(
        self,
        component: Component,
        renderer: ComponentRenderer,
        choices: list[ChoiceButtonConfig],
        get_value: Optional[Callable[[Any], Output_co]] = None,
    ):
        super().__init__(
            component=component,
            renderer=renderer,
            get_value=get_value,
        )
        self._choice_buttons = choices

    @override
    def __await__(self) -> Generator[Any, None, ChoiceReturn[Output_co]]:
        return_values, choice = yield from self._renderer(
            [self._component], self._handle_validation, self._choice_buttons
        ).__await__()
        return ChoiceReturn(
            choice=cast(str, choice),
            return_value=self._get_value(return_values[0]),
        )

    @overload
    def optional(
        self,
        optional: Literal[True] = True,
    ) -> "WithChoicesOptionalIOPromise[Input_MN_co, Optional[Output_co]]":
        ...

    @overload
    def optional(
        self: WithChoicesInputIOPromiseSelf,
        optional: Literal[False],
    ) -> WithChoicesInputIOPromiseSelf:
        ...

    @overload
    def optional(
        self: WithChoicesInputIOPromiseSelf,
        optional: bool,
    ) -> "Union[WithChoicesOptionalIOPromise[Input_MN_co, Optional[Output_co]], WithChoicesInputIOPromiseSelf]":
        ...

    def optional(
        self: WithChoicesInputIOPromiseSelf,
        optional: bool = True,
    ) -> "Union[WithChoicesOptionalIOPromise[Input_MN_co, Optional[Output_co]], WithChoicesInputIOPromiseSelf]":
        return (
            WithChoicesOptionalIOPromise[Input_MN_co, Optional[Output_co]](
                self._component,
                self._renderer,
                choices=self._choice_buttons,
                get_value=self._value_getter,
            )
            if optional
            else self
        )

    @override
    def validate(
        self: WithChoicesInputIOPromiseSelf,
        validator: Optional[WithChoicesIOGroupPromiseValidator[Output_co]],
    ) -> WithChoicesInputIOPromiseSelf:
        self._component.validator = None
        self._validator = validator
        return self

    async def _handle_validation(self, ret: ChoiceReturn[list[Any]]):
        if self._validator is None:
            return None

        value = (
            self._get_value(ret.return_value[0])
            if self._value_getter is not None
            else ret.return_value[0]
        )

        validate_ret = self._validator(
            ChoiceReturn(choice=ret.choice, return_value=value)
        )

        return cast(
            Optional[str],
            await validate_ret if inspect.isawaitable(validate_ret) else validate_ret,
        )


WithChoicesMultipleableIOPromiseSelf = TypeVar(
    "WithChoicesMultipleableIOPromiseSelf", bound="WithChoicesMultipleableIOPromise"
)


class WithChoicesMultipleableIOPromise(
    MultipleableIOPromise[Multipleable_MN_co, Output_co, DefaultValue]
):
    _choice_buttons: list[ChoiceButtonConfig]
    _validator: Optional[WithChoicesIOGroupPromiseValidator[Output_co]] = None

    def __init__(
        self,
        component: Component,
        renderer: ComponentRenderer,
        choices: list[ChoiceButtonConfig],
        get_value: Optional[Callable[[Any], Output_co]] = None,
    ):
        super().__init__(
            component=component,
            renderer=renderer,
            get_value=get_value,
        )
        self._choice_buttons = parse_obj_as(list[ChoiceButtonConfig], choices)

    @override
    def __await__(self) -> Generator[Any, None, ChoiceReturn[Output_co]]:
        return_values, choice = yield from self._renderer(
            [self._component], self._handle_validation, self._choice_buttons
        ).__await__()
        return ChoiceReturn(
            choice=cast(str, choice),
            return_value=self._get_value(return_values[0]),
        )

    def multiple(self, *, default_value: Optional[Iterable[DefaultValue]] = None):
        multiple_io_promise = super().multiple(default_value=default_value)
        return WithChoicesMultipleIOPromise[
            Multipleable_MN_co, Output_co, DefaultValue
        ](
            component=multiple_io_promise._component,
            renderer=multiple_io_promise._renderer,
            get_value=self._value_getter,
            choices=self._choice_buttons,
        )

    @override
    def validate(
        self: WithChoicesMultipleableIOPromiseSelf,
        validator: Optional[WithChoicesIOGroupPromiseValidator[Output_co]],
    ) -> WithChoicesMultipleableIOPromiseSelf:
        self._component.validator = None
        self._validator = validator
        return self

    async def _handle_validation(self, ret: ChoiceReturn[list[Any]]):
        if self._validator is None:
            return None

        value = (
            self._get_value(ret.return_value[0])
            if self._value_getter is not None
            else ret.return_value[0]
        )

        validate_ret = self._validator(
            ChoiceReturn(choice=ret.choice, return_value=value)
        )

        return cast(
            Optional[str],
            await validate_ret if inspect.isawaitable(validate_ret) else validate_ret,
        )


WithChoicesMultipleIOPromiseSelf = TypeVar(
    "WithChoicesMultipleIOPromiseSelf", bound="WithChoicesMultipleIOPromise"
)


class WithChoicesMultipleIOPromise(
    MultipleIOPromise[Multipleable_MN_co, Output_co, DefaultValue]
):
    _choice_buttons: list[ChoiceButtonConfig]
    _validator: Optional[WithChoicesIOGroupPromiseValidator[list[Output_co]]] = None

    def __init__(
        self,
        component: Component,
        renderer: ComponentRenderer,
        choices: list[ChoiceButtonConfig],
        get_value: Optional[Callable[[Any], Output_co]] = None,
    ):
        super().__init__(
            component=component,
            renderer=renderer,
            get_value=get_value,
        )
        self._choice_buttons = choices

    @override
    def __await__(self) -> Generator[Any, None, ChoiceReturn[list[Output_co]]]:
        return_values, choice = yield from self._renderer(
            [self._component], self._handle_validation, self._choice_buttons
        ).__await__()
        return ChoiceReturn(
            choice=cast(str, choice),
            return_value=self._get_value(return_values[0]),
        )

    @override
    def validate(
        self: WithChoicesMultipleIOPromiseSelf,
        validator: Optional[WithChoicesIOGroupPromiseValidator[list[Output_co]]],
    ) -> WithChoicesMultipleIOPromiseSelf:
        self._component.validator = None
        self._validator = validator
        return self

    async def _handle_validation(self, ret: ChoiceReturn[list[Any]]):
        if self._validator is None:
            return None

        value = (
            self._get_value(ret.return_value[0])
            if self._value_getter is not None
            else ret.return_value[0]
        )

        validate_ret = self._validator(
            ChoiceReturn(choice=ret.choice, return_value=value)
        )

        return cast(
            Optional[str],
            await validate_ret if inspect.isawaitable(validate_ret) else validate_ret,
        )


IOGroupPromiseSelf = TypeVar("IOGroupPromiseSelf", bound="IOGroupPromise")


class KeyedIONamespace(Mapping):
    __items: dict[str, Any] = {}

    def __init__(self, **kwargs: Any):
        self.__items = kwargs

    def __repr__(self) -> str:
        items = ", ".join([f"{k}={v}" for k, v in self.__items.items()])
        return f"KeyedIONamespace({items})"

    def __getattr__(self, name: str) -> Any:
        return self.__items[name]

    def __getitem__(self, name: str) -> Any:
        return self.__items[name]

    def __len__(self) -> int:
        return len(self.__items)

    def __iter__(self) -> Iterator[str]:
        yield from self.__items.keys()

    def __contains__(self, key: str) -> bool:
        return key in self.__items


class IOGroupPromise(Generic[Unpack[GroupOutput]]):
    _io_promises: tuple[GroupableIOPromise[MethodName, Any], ...]
    _kw_io_promises: Optional[dict[str, GroupableIOPromise[MethodName, Any]]] = None
    _renderer: ComponentRenderer
    _validator: "Optional[IOGroupPromiseValidator[Unpack[GroupOutput]]]" = None
    _choice_buttons: Optional[list[ChoiceButtonConfig]] = None

    def __init__(
        self,
        renderer: ComponentRenderer,
        io_promises: tuple[GroupableIOPromise[MethodName, Any], ...],
        kw_io_promises: Optional[dict[str, GroupableIOPromise[MethodName, Any]]] = None,
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

    def __await__(self) -> Generator[Any, None, Union[tuple[Unpack[GroupOutput]], KeyedIONamespace, ChoiceReturn]]:  # type: ignore
        if self._kw_io_promises is not None and len(self._kw_io_promises) > 0:
            return_values, _choice = yield from self._renderer(
                [p._component for p in self._kw_io_promises.values()],
                self._handle_validation,
                self._choice_buttons,
            ).__await__()
            res_dict = {
                key: return_values[i]
                for i, key in enumerate(self._kw_io_promises.keys())
            }
            return KeyedIONamespace(**res_dict)
        else:
            return_values, _choice = yield from self._renderer(
                [p._component for p in self._io_promises],
                self._handle_validation,
                self._choice_buttons,
            ).__await__()
            return cast(
                tuple[Unpack[GroupOutput]],
                [
                    self._io_promises[i]._get_value(val)
                    for (i, val) in enumerate(return_values)
                ],
            )

    async def _handle_validation(self, ret: ChoiceReturn[list[Any]]) -> Optional[str]:
        if self._validator is None:
            return None

        if self._kw_io_promises is not None and len(self._kw_io_promises) > 0:
            io_promises = list(self._kw_io_promises.values())
            values = {
                key: io_promises[index]._get_value(ret.return_value[index])
                for index, key in enumerate(self._kw_io_promises.keys())
            }
            ret = self._validator(**values)  # type: ignore
        else:
            io_promises = self._io_promises
            values = [
                io_promises[index]._get_value(v)
                for index, v in enumerate(ret.return_value)
            ]
            ret = self._validator(*values)  # type: ignore
        return cast(Optional[str], await ret if inspect.isawaitable(ret) else ret)

    @overload
    def validate(
        self: "IOGroupPromise[KeyedIONamespace]",
        validator: "Callable[..., Optional[Union[str, Awaitable[Optional[str]]]]]",
    ) -> "IOGroupPromise[Unpack[GroupOutput]]":
        ...

    @overload
    def validate(
        self: "IOGroupPromise[Unpack[GroupOutput]]",
        validator: "Optional[IOGroupPromiseValidator[Unpack[GroupOutput]]]",
    ) -> "IOGroupPromise[Unpack[GroupOutput]]":
        ...

    def validate(  # type: ignore
        self: "IOGroupPromise[Unpack[GroupOutput]]",
        validator: "Optional[IOGroupPromiseValidator[Unpack[GroupOutput]]]",
    ) -> "IOGroupPromise[Unpack[GroupOutput]]":
        self._validator = validator
        return self

    def continue_button_options(
        self: "IOGroupPromise[Unpack[GroupOutput]]",
        label: Optional[str] = None,
        theme: Optional[ButtonTheme] = None,
    ) -> "IOGroupPromise[Unpack[GroupOutput]]":
        """Deprecated. Please use .with_choices() instead."""
        self._choice_buttons = [
            ChoiceButtonConfig(
                label=label if label is not None else "Continue",
                value=label if label is not None else "Continue",
                theme=theme,
            )
        ]
        return self

    def with_choices(
        self: "IOGroupPromise[Unpack[GroupOutput]]",
        choices: Iterable[Union[ChoiceButton, str]],
    ) -> "WithChoicesIOGroupPromise[Unpack[GroupOutput]]":
        return WithChoicesIOGroupPromise(
            inner_promise=self,
            choices=[
                ChoiceButtonConfig.parse_obj(
                    {"label": item, "value": item} if isinstance(item, str) else item
                )
                for item in choices
            ],
        )


class WithChoicesIOGroupPromise(Generic[Unpack[GroupOutput]]):
    _inner_promise: IOGroupPromise[Unpack[GroupOutput]]
    _choice_buttons: Optional[list[ChoiceButtonConfig]] = None
    _validator: Optional[
        WithChoicesIOGroupPromiseValidator[tuple[Unpack[GroupOutput]]]
    ] = None

    def __init__(
        self,
        inner_promise: IOGroupPromise[Unpack[GroupOutput]],
        choices: list[ChoiceButtonConfig],
        validator: "Optional[IOGroupPromiseValidator[Unpack[GroupOutput]]]" = None,
    ):
        self._inner_promise = inner_promise
        self._choice_buttons = choices

        if validator is not None:

            def new_validator(ret: ChoiceReturn[tuple[Unpack[GroupOutput]]]):
                return validator(*ret.return_value)

            self._validator = new_validator

    @overload
    def __await__(
        self: "WithChoicesIOGroupPromise[KeyedIONamespace]",
    ) -> Generator[Any, None, ChoiceReturn[KeyedIONamespace]]:
        """Fallback typing for calls with keyword arguments."""
        ...

    @overload
    def __await__(
        self: "WithChoicesIOGroupPromise[list[Any]]",
    ) -> Generator[Any, None, ChoiceReturn[list[Any]]]:
        """Fallback typing for calls with 10 or more arguments."""
        ...

    @overload
    def __await__(
        self,
    ) -> Generator[Any, None, ChoiceReturn[tuple[Unpack[GroupOutput]]]]:
        ...

    def __await__(self) -> Generator[Any, None, ChoiceReturn[Union[tuple[Unpack[GroupOutput]], KeyedIONamespace]]]:  # type: ignore
        if (
            self._inner_promise._kw_io_promises is not None
            and len(self._inner_promise._kw_io_promises) > 0
        ):
            return_values, choice = yield from self._inner_promise._renderer(
                [p._component for p in self._inner_promise._kw_io_promises.values()],
                self._handle_validation,
                self._choice_buttons,
            ).__await__()
            res_dict = {
                key: return_values[i]
                for i, key in enumerate(self._inner_promise._kw_io_promises.keys())
            }
            return ChoiceReturn(
                choice=cast(str, choice),
                return_value=KeyedIONamespace(**res_dict),
            )
        else:
            return_values, choice = yield from self._inner_promise._renderer(
                [p._component for p in self._inner_promise._io_promises],
                self._handle_validation,
                self._choice_buttons,
            ).__await__()
            return ChoiceReturn(
                choice=cast(str, choice),
                return_value=cast(
                    tuple[Unpack[GroupOutput]],
                    [
                        self._inner_promise._io_promises[i]._get_value(val)
                        for (i, val) in enumerate(return_values)
                    ],
                ),
            )

    @overload
    def validate(
        self: "WithChoicesIOGroupPromise[KeyedIONamespace]",
        validator: "Callable[..., Optional[Union[str, Awaitable[Optional[str]]]]]",
    ) -> "WithChoicesIOGroupPromise[Unpack[GroupOutput]]":
        ...

    @overload
    def validate(
        self: "WithChoicesIOGroupPromise[Unpack[GroupOutput]]",
        validator: "Optional[WithChoicesIOGroupPromiseValidator[tuple[Unpack[GroupOutput]]]]",
    ) -> "WithChoicesIOGroupPromise[Unpack[GroupOutput]]":
        ...

    def validate(  # type: ignore
        self: "WithChoicesIOGroupPromise[Unpack[GroupOutput]]",
        validator: "Optional[WithChoicesIOGroupPromiseValidator[tuple[Unpack[GroupOutput]]]]",
    ) -> "WithChoicesIOGroupPromise[Unpack[GroupOutput]]":
        self._validator = validator
        return self

    def with_choices(
        self: "WithChoicesIOGroupPromise[Unpack[GroupOutput]]",
        choices: Iterable[Union[ChoiceButton, str]],
    ) -> "WithChoicesIOGroupPromise[Unpack[GroupOutput]]":
        self._choice_buttons = [
            ChoiceButtonConfig.parse_obj(
                {"label": item, "value": item} if isinstance(item, str) else item
            )
            for item in choices
        ]
        return self

    async def _handle_validation(self, ret: ChoiceReturn[list[Any]]) -> Optional[str]:
        if self._validator is None:
            return None

        if (
            self._inner_promise._kw_io_promises is not None
            and len(self._inner_promise._kw_io_promises) > 0
        ):
            io_promises = list(self._inner_promise._kw_io_promises.values())
            values = {
                key: io_promises[index]._get_value(ret.return_value[index])
                for index, key in enumerate(self._inner_promise._kw_io_promises.keys())
            }
            validate_ret = self._validator(ChoiceReturn(choice=ret.choice, return_value=values))  # type: ignore
        else:
            io_promises = self._inner_promise._io_promises
            values = [
                io_promises[index]._get_value(v)
                for index, v in enumerate(ret.return_value)
            ]
            validate_ret = self._validator(ChoiceReturn(choice=ret.choice, return_value=values))  # type: ignore
        return cast(
            Optional[str],
            await validate_ret if inspect.isawaitable(validate_ret) else validate_ret,
        )
