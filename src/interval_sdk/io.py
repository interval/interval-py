from dataclasses import dataclass
from datetime import date, datetime, time
from typing import overload, Tuple

from .io_schema import *
from .component import (
    IODatePromise,
    IOTimePromise,
    IODateTimePromise,
    IOPromise,
    GroupableIOPromise,
    ExclusiveIOPromise,
    Component,
    ComponentRenderer,
)
from .types import KeyValueObject

from pydantic import parse_obj_as

_T1 = TypeVar("_T1")
_T2 = TypeVar("_T2")
_T3 = TypeVar("_T3")
_T4 = TypeVar("_T4")
_T5 = TypeVar("_T5")
_T6 = TypeVar("_T6")
_T7 = TypeVar("_T7")
_T8 = TypeVar("_T8")


class IO:
    @dataclass
    class Input:
        _renderer: ComponentRenderer

        def text(
            self,
            label: str,
            help_text: str | None = None,
            default_value: str | None = None,
            multiline: bool | None = None,
            lines: int | None = None,
        ) -> IOPromise[Literal["INPUT_TEXT"], str]:
            c = Component(
                method_name="INPUT_TEXT",
                label=label,
                initial_props=InputTextProps(
                    help_text=help_text,
                    default_value=default_value,
                    multiline=multiline,
                    lines=lines,
                ).dict(),
            )
            return IOPromise(c, renderer=self._renderer)

        def email(
            self,
            label: str,
            help_text: str | None = None,
            default_value: str | None = None,
        ) -> IOPromise[Literal["INPUT_EMAIL"], str]:
            c = Component(
                method_name="INPUT_EMAIL",
                label=label,
                initial_props=InputEmailProps(
                    help_text=help_text,
                    default_value=default_value,
                ).dict(),
            )
            return IOPromise(c, renderer=self._renderer)

        def number(
            self,
            label: str,
            min: int | None = None,
            max: int | None = None,
            prepend: str | None = None,
            help_text: str | None = None,
            default_value: str | None = None,
        ) -> IOPromise[Literal["INPUT_NUMBER"], int]:
            c = Component(
                method_name="INPUT_NUMBER",
                label=label,
                initial_props=InputNumberProps(
                    min=min,
                    max=max,
                    prepend=prepend,
                    help_text=help_text,
                    default_value=default_value,
                ).dict(),
            )
            return IOPromise(c, renderer=self._renderer)

        def boolean(
            self,
            label: str,
            help_text: str | None = None,
            default_value: str | None = None,
        ) -> IOPromise[Literal["INPUT_BOOLEAN"], bool]:
            c = Component(
                method_name="INPUT_BOOLEAN",
                label=label,
                initial_props=InputBooleanProps(
                    help_text=help_text,
                    default_value=default_value,
                ).dict(),
            )
            return IOPromise(c, renderer=self._renderer)

        def rich_text(
            self,
            label: str,
            help_text: str | None = None,
        ) -> IOPromise[Literal["INPUT_RICH_TEXT"], str]:
            c = Component(
                method_name="INPUT_RICH_TEXT",
                label=label,
                initial_props=InputRichTextProps(
                    help_text=help_text,
                ).dict(),
            )
            return IOPromise(c, renderer=self._renderer)

        def spreadsheet(
            self,
            label: str,
            columns: dict[str, TypeValue],
            help_text: str | None = None,
            # XXX: Don't think better type is possible here?
        ) -> IOPromise[Literal["INPUT_SPREADSHEET"], list]:
            c = Component(
                method_name="INPUT_SPREADSHEET",
                label=label,
                initial_props=InputSpreadsheetProps(
                    help_text=help_text,
                    columns=columns,
                ).dict(),
            )
            return IOPromise(c, renderer=self._renderer)

    @dataclass
    class Select:
        _renderer: ComponentRenderer

        def table(
            self,
            label: str,
            data: list[TableRow],
            help_text: str | None = None,
            columns: TableColumnDef | None = None,
        ) -> IOPromise[Literal["SELECT_TABLE"], list[TableRow]]:
            c = Component(
                method_name="SELECT_TABLE",
                label=label,
                initial_props=SelectTableProps(
                    help_text=help_text,
                    columns=columns,
                    data=data,
                ).dict(),
            )
            return IOPromise(c, renderer=self._renderer)

        def single(
            self,
            label: str,
            options: list[RichSelectOption],
            help_text: str | None = None,
            default_value: RichSelectOption | None = None,
            searchable: bool | None = None,
        ) -> IOPromise[Literal["SELECT_SINGLE"], RichSelectOption]:
            c = Component(
                method_name="SELECT_SINGLE",
                label=label,
                initial_props=SelectSingleProps(
                    options=[
                        parse_obj_as(RichSelectOptionModel, option)
                        for option in options
                    ],
                    help_text=help_text,
                    default_value=parse_obj_as(RichSelectOptionModel, default_value)
                    if default_value is not None
                    else None,
                    searchable=searchable,
                ).dict(),
            )
            return IOPromise(c, renderer=self._renderer)

        def multiple(
            self,
            label: str,
            options: list[LabelValue],
            help_text: str | None = None,
            default_value: list[LabelValue] = [],
        ) -> IOPromise[Literal["SELECT_MULTIPLE"], list[LabelValue]]:
            c = Component(
                method_name="SELECT_MULTIPLE",
                label=label,
                initial_props=SelectMultipleProps(
                    options=options,
                    help_text=help_text,
                    default_value=default_value,
                ).dict(),
            )
            return IOPromise(c, renderer=self._renderer)

    @dataclass
    class Display:
        _renderer: ComponentRenderer

        def heading(
            self,
            label: str,
        ) -> IOPromise[Literal["DISPLAY_HEADING"], None]:
            c = Component(
                method_name="DISPLAY_HEADING",
                label=label,
                initial_props={},
            )
            return IOPromise(c, renderer=self._renderer)

        def markdown(
            self,
            label: str,
        ) -> IOPromise[Literal["DISPLAY_MARKDOWN"], None]:
            c = Component(
                method_name="DISPLAY_MARKDOWN",
                label=label,
                initial_props={},
            )
            return IOPromise(c, renderer=self._renderer)

        def object(
            self,
            label: str,
            data: KeyValueObject,
        ) -> IOPromise[Literal["DISPLAY_OBJECT"], None]:
            c = Component(
                method_name="DISPLAY_OBJECT",
                label=label,
                initial_props=DisplayObjectProps(
                    data=KeyValueObjectModel.parse_obj(data),
                ).dict(),
            )
            return IOPromise(c, renderer=self._renderer)

        def table(
            self,
            label: str,
            data: list[
                dict[
                    str,
                    str
                    | int
                    | float
                    | bool
                    | None
                    | date
                    | datetime
                    | TableRowLabelValue,
                ]
            ],
            help_text: str | None = None,
            columns: list[TableColumnDef] | None = None,
        ) -> IOPromise[Literal["DISPLAY_TABLE"], None]:
            c = Component(
                method_name="DISPLAY_TABLE",
                label=label,
                initial_props=DisplayTableProps(
                    help_text=help_text,
                    columns=columns,
                    data=data,
                ).dict(),
            )
            return IOPromise(c, renderer=self._renderer)

    @dataclass
    class Experimental:
        @dataclass
        class Progress:
            _renderer: ComponentRenderer

            def progress_steps(
                self,
                label: str,
                steps: DisplayProgressStepsSteps,
                current_step: int | None = None,
                subtitle: str | None = None,
            ) -> IOPromise[Literal["DISPLAY_PROGRESS_STEPS"], None]:
                c = Component(
                    method_name="DISPLAY_PROGRESS_STEPS",
                    label=label,
                    initial_props=DisplayProgressStepsProps(
                        steps=steps,
                        current_step=current_step,
                        subtitle=subtitle,
                    ).dict(),
                )
                return IOPromise(c, renderer=self._renderer)

            def progress_indeterminate(
                self,
                label: str,
            ) -> IOPromise[Literal["DISPLAY_PROGRESS_INDETERMINATE"], None]:
                c = Component(
                    method_name="DISPLAY_PROGRESS_INDETERMINATE",
                    label=label,
                    initial_props={},
                )
                return IOPromise(c, renderer=self._renderer)

            def progress_through_list(
                self,
                label: str,
                items: list[DisplayProgressthroughListItem],
            ) -> IOPromise[Literal["DISPLAY_PROGRESS_THROUGH_LIST"], None]:
                c = Component(
                    method_name="DISPLAY_PROGRESS_THROUGH_LIST",
                    label=label,
                    initial_props=DisplayProgressThroughListProps(
                        items=items,
                    ).dict(),
                )
                return IOPromise(c, renderer=self._renderer)

        def date(
            self,
            label: str,
            help_text: str | None = None,
            default_value: date | None = None,
        ) -> IODatePromise:
            model_default = None
            if default_value is not None:
                model_default = DateModel(
                    year=default_value.year,
                    month=default_value.month,
                    day=default_value.day,
                )
            c = Component(
                method_name="INPUT_DATE",
                label=label,
                initial_props=InputDateProps(
                    help_text=help_text,
                    default_value=model_default,
                ).dict(),
            )
            return IODatePromise(c, renderer=self._renderer)

        def time(
            self,
            label: str,
            help_text: str | None = None,
            default_value: time | None = None,
        ) -> IOTimePromise:
            model_default = None
            if default_value is not None:
                model_default = TimeModel(
                    hour=default_value.hour,
                    minute=default_value.minute,
                )
            c = Component(
                method_name="INPUT_TIME",
                label=label,
                initial_props=InputTimeProps(
                    help_text=help_text,
                    default_value=model_default,
                ).dict(),
            )
            return IOTimePromise(c, renderer=self._renderer)

        def datetime(
            self,
            label: str,
            help_text: str | None = None,
            default_value: datetime | None = None,
        ) -> IODateTimePromise:
            model_default = None
            if default_value is not None:
                model_default = DateTimeModel(
                    year=default_value.year,
                    month=default_value.month,
                    day=default_value.day,
                    hour=default_value.hour,
                    minute=default_value.minute,
                )
            c = Component(
                method_name="INPUT_DATETIME",
                label=label,
                initial_props=InputDateTimeProps(
                    help_text=help_text,
                    default_value=model_default,
                ).dict(),
            )
            return IODateTimePromise(c, renderer=self._renderer)

        _renderer: ComponentRenderer
        progress: Progress

        def __init__(self, renderer: ComponentRenderer):
            self._renderer = renderer
            self.progress = IO.Experimental.Progress(renderer)

    _renderer: ComponentRenderer
    input: Input
    select: Select
    display: Display
    experimental: Experimental

    def __init__(
        self,
        renderer: ComponentRenderer,
    ):
        self._renderer = renderer
        self.input = self.Input(renderer)
        self.select = self.Select(renderer)
        self.display = self.Display(renderer)
        self.experimental = self.Experimental(renderer)

    def confirm(
        self,
        label: str,
        help_text: str | None = None,
    ) -> ExclusiveIOPromise[Literal["CONFIRM"], bool]:
        c = Component(
            method_name="CONFIRM",
            label=label,
            initial_props=ConfirmProps(
                help_text=help_text,
            ).dict(),
        )
        return ExclusiveIOPromise(c, renderer=self._renderer)

    # Based on typing for asyncio.gather
    # https://github.com/python/typeshed/blob/4d23919200d9e89486f4d9e2587f82314d4af0f6/stdlib/asyncio/tasks.pyi#L82-L165
    @overload
    async def group(self, p1: GroupableIOPromise[MethodName, _T1]) -> Tuple[_T1]:
        """
        Actually returns a list, claims to return a tuple because lists do not support
        variadic types.
        """
        ...

    @overload
    async def group(
        self,
        p1: GroupableIOPromise[MethodName, _T1],
        p2: GroupableIOPromise[MethodName, _T2],
    ) -> Tuple[_T1, _T2]:
        ...

    @overload
    async def group(
        self,
        p1: GroupableIOPromise[MethodName, _T1],
        p2: GroupableIOPromise[MethodName, _T2],
        p3: GroupableIOPromise[MethodName, _T3],
    ) -> Tuple[_T1, _T2, _T3]:
        ...

    @overload
    async def group(
        self,
        p1: GroupableIOPromise[MethodName, _T1],
        p2: GroupableIOPromise[MethodName, _T2],
        p3: GroupableIOPromise[MethodName, _T3],
        p4: GroupableIOPromise[MethodName, _T4],
    ) -> Tuple[_T1, _T2, _T3, _T4]:
        ...

    @overload
    async def group(
        self,
        p1: GroupableIOPromise[MethodName, _T1],
        p2: GroupableIOPromise[MethodName, _T2],
        p3: GroupableIOPromise[MethodName, _T3],
        p4: GroupableIOPromise[MethodName, _T4],
        p5: GroupableIOPromise[MethodName, _T5],
        p6: GroupableIOPromise[MethodName, _T6],
    ) -> Tuple[_T1, _T2, _T3, _T4, _T5, _T6]:
        ...

    @overload
    async def group(
        self,
        p1: GroupableIOPromise[MethodName, _T1],
        p2: GroupableIOPromise[MethodName, _T2],
        p3: GroupableIOPromise[MethodName, _T3],
        p4: GroupableIOPromise[MethodName, _T4],
        p5: GroupableIOPromise[MethodName, _T5],
        p6: GroupableIOPromise[MethodName, _T6],
        p7: GroupableIOPromise[MethodName, _T7],
    ) -> Tuple[_T1, _T2, _T3, _T4, _T5, _T6, _T7]:
        ...

    @overload
    async def group(
        self,
        p1: GroupableIOPromise[MethodName, _T1],
        p2: GroupableIOPromise[MethodName, _T2],
        p3: GroupableIOPromise[MethodName, _T3],
        p4: GroupableIOPromise[MethodName, _T4],
        p5: GroupableIOPromise[MethodName, _T5],
        p6: GroupableIOPromise[MethodName, _T6],
        p7: GroupableIOPromise[MethodName, _T7],
        p8: GroupableIOPromise[MethodName, _T8],
    ) -> Tuple[_T1, _T2, _T3, _T4, _T5, _T6, _T7, _T8]:
        ...

    @overload
    async def group(
        self, *io_promises: GroupableIOPromise[MethodName, Any]
    ) -> list[Any]:
        ...

    async def group(self, *io_promises: GroupableIOPromise[MethodName, Any]):  # type: ignore
        raw_values = await self._renderer([p.component for p in io_promises])
        return [io_promises[i]._get_value(val) for (i, val) in enumerate(raw_values)]
