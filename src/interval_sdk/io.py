import base64
import sys
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import overload, Tuple
from urllib.parse import ParseResult, urlparse

from .io_schema import *
from .classes.component import (
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

TR = TypeVar("TR", bound=Mapping[str, TableRowValue])

MAX_FILE_SIZE_MB = 50


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

        @overload
        def number(
            self,
            label: str,
            min: float | int | None = None,
            max: float | int | None = None,
            prepend: str | None = None,
            help_text: str | None = None,
            default_value: float | int | None = None,
            decimals: None = None,
        ) -> IOPromise[Literal["INPUT_NUMBER"], int]:
            ...

        @overload
        def number(
            self,
            label: str,
            min: float | int | None = None,
            max: float | int | None = None,
            prepend: str | None = None,
            help_text: str | None = None,
            default_value: float | int | None = None,
            decimals: int = 0,
        ) -> IOPromise[Literal["INPUT_NUMBER"], float]:
            ...

        def number(
            self,
            label: str,
            min: float | int | None = None,
            max: float | int | None = None,
            prepend: str | None = None,
            help_text: str | None = None,
            default_value: float | int | None = None,
            decimals: int | None = None,
        ):
            c = Component(
                method_name="INPUT_NUMBER",
                label=label,
                initial_props=InputNumberProps(
                    min=min,
                    max=max,
                    prepend=prepend,
                    help_text=help_text,
                    default_value=default_value,
                    decimals=decimals,
                ).dict(),
            )

            def get_value(val: Any):
                if decimals is None:
                    return int(val)

                return val

            return IOPromise(c, renderer=self._renderer, get_value=get_value)

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

        def url(
            self,
            label: str,
            help_text: str | None = None,
            allowed_protocols: list[str] | None = None,
            default_value: str | None = None,
        ) -> IOPromise[Literal["INPUT_URL"], ParseResult]:
            c = Component(
                method_name="INPUT_URL",
                label=label,
                initial_props=InputUrlProps(
                    help_text=help_text,
                    allowed_protocols=allowed_protocols,
                    default_value=default_value,
                ).dict(),
            )

            def get_value(val: Any) -> ParseResult:
                return urlparse(val)

            return IOPromise(c, renderer=self._renderer, get_value=get_value)

        def date(
            self,
            label: str,
            help_text: str | None = None,
            default_value: date | None = None,
        ) -> IOPromise[Literal["INPUT_DATE"], date]:
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

            def get_value(val: Any) -> date:
                obj: DateModel = val

                return date(obj.year, obj.month, obj.day)

            return IOPromise(c, renderer=self._renderer, get_value=get_value)

        def time(
            self,
            label: str,
            help_text: str | None = None,
            default_value: time | None = None,
        ) -> IOPromise[Literal["INPUT_TIME"], time]:
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

            def get_value(val: Any) -> time:
                obj: TimeModel = val

                return time(obj.hour, obj.minute)

            return IOPromise(c, renderer=self._renderer, get_value=get_value)

        def datetime(
            self,
            label: str,
            help_text: str | None = None,
            default_value: datetime | None = None,
        ) -> IOPromise[Literal["INPUT_DATETIME"], datetime]:
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

            def get_value(val: Any) -> datetime:
                obj: DateTimeModel = val

                return datetime(obj.year, obj.month, obj.day, obj.hour, obj.minute)

            return IOPromise(c, renderer=self._renderer, get_value=get_value)

    @dataclass
    class Select:
        _renderer: ComponentRenderer

        def table(
            self,
            label: str,
            data: list[TR],
            help_text: str | None = None,
            columns: list[TableColumnDef] | None = None,
            min_selections: int | None = None,
            max_selections: int | None = None,
        ) -> IOPromise[Literal["SELECT_TABLE"], list[TR]]:
            serialized = [
                InternalTableRowModel.parse_obj(
                    serialize_table_row(i, cast(dict, row), columns)
                )
                for (i, row) in enumerate(data)
            ]
            c = Component(
                method_name="SELECT_TABLE",
                label=label,
                initial_props=SelectTableProps(
                    help_text=help_text,
                    columns=[{"label": col["label"]} for col in columns]
                    if columns is not None
                    else None,
                    data=serialized,
                    min_selections=min_selections,
                    max_selections=max_selections,
                ).dict(),
            )

            def get_value(val: Any) -> list[TR]:
                indices = [int(row.key) for row in val]
                rows = [row for (i, row) in enumerate(data) if i in indices]
                return rows

            return IOPromise(c, renderer=self._renderer, get_value=get_value)

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
            options: list[PassthroughLabelValue],
            help_text: str | None = None,
            default_value: list[PassthroughLabelValue] = [],
            min_selections: int | None = None,
            max_selections: int | None = None,
        ) -> IOPromise[Literal["SELECT_MULTIPLE"], list[PassthroughLabelValue]]:
            c = Component(
                method_name="SELECT_MULTIPLE",
                label=label,
                initial_props=SelectMultipleProps(
                    options=[
                        PassthroughLabelValueModel[PassthroughLabelValue].parse_obj(
                            option
                        )
                        for option in options
                    ],
                    help_text=help_text,
                    default_value=[
                        PassthroughLabelValueModel[PassthroughLabelValue].parse_obj(val)
                        for val in default_value
                    ],
                    min_selections=min_selections,
                    max_selections=max_selections,
                ).dict(),
            )

            option_map = {option["value"]: option for option in options}

            def get_value(
                val: list[PassthroughLabelValue],
            ) -> list[PassthroughLabelValue]:
                return [option_map[item["value"]] for item in val]

            return IOPromise(c, renderer=self._renderer, get_value=get_value)

    @dataclass
    class Display:
        _renderer: ComponentRenderer

        def code(
            self,
            label: str,
            code: str,
            language: str | None = None,
        ) -> IOPromise[Literal["DISPLAY_CODE"], None]:
            c = Component(
                method_name="DISPLAY_CODE",
                label=label,
                initial_props=DisplayCodeProps(
                    code=code,
                    language=language,
                ).dict(),
            )
            return IOPromise(c, renderer=self._renderer)

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

        def metadata(
            self,
            label: str,
            layout: MetadataLayout,
            data: KeyValueObject,
        ) -> IOPromise[Literal["DISPLAY_METADATA"], None]:
            c = Component(
                method_name="DISPLAY_METADATA",
                label=label,
                initial_props=DisplayMetadataProps(
                    layout=layout,
                    data=KeyValueObjectModel.parse_obj(data),
                ).dict(),
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

        def image(
            self,
            label: str,
            url: str | None = None,
            bytes: bytes | None = None,
            alt: str | None = None,
            height: ImageSize | None = None,
            size: ImageSize | None = None,
            width: ImageSize | None = None,
        ) -> IOPromise[Literal["DISPLAY_IMAGE"], None]:
            if bytes is not None and url is None:
                if sys.getsizeof(bytes) > MAX_FILE_SIZE_MB * 1000 * 1000:
                    raise ValueError(
                        f"Image bytes must be less than {MAX_FILE_SIZE_MB}MB"
                    )
                data = base64.b64encode(bytes).decode("utf-8")
                if data[0] == "i":
                    mime = "image/png"
                elif data[0] == "R":
                    mime = "image/gif"
                elif data[0] == "/":
                    mime = "image/jpeg"
                elif data[0] == "U":
                    mime = "image/webp"
                else:
                    mime = "image/unknown"
                url = f"data:{mime};base64,{data}"
            c = Component(
                method_name="DISPLAY_IMAGE",
                label=label,
                initial_props=DisplayImageProps(
                    url=url,
                    alt=alt,
                    height=height if height is not None else size,
                    width=width if width is not None else size,
                ).dict(),
            )
            return IOPromise(c, renderer=self._renderer)

        def table(
            self,
            label: str,
            data: list[TR],
            help_text: str | None = None,
            columns: list[TableColumnDef] | None = None,
        ) -> IOPromise[Literal["DISPLAY_TABLE"], None]:
            serialized = [
                InternalTableRowModel.parse_obj(serialize_table_row(i, row, columns))
                for (i, row) in enumerate(data)
            ]
            c = Component(
                method_name="DISPLAY_TABLE",
                label=label,
                initial_props=DisplayTableProps(
                    help_text=help_text,
                    columns=[{"label": col["label"]} for col in columns]
                    if columns is not None
                    else None,
                    data=serialized,
                ).dict(),
            )
            return IOPromise(c, renderer=self._renderer)

        def video(
            self,
            label: str,
            url: str | None = None,
            alt: str | None = None,
            bytes: bytes | None = None,
            loop: bool = False,
            muted: bool = False,
            size: ImageSize | None = None,
            height: ImageSize | None = None,
            width: ImageSize | None = None,
        ) -> IOPromise[Literal["DISPLAY_VIDEO"], None]:
            if bytes is not None and url is None:
                if sys.getsizeof(bytes) > MAX_FILE_SIZE_MB * 1000 * 1000:
                    raise ValueError(
                        f"Video bytes must be less than {MAX_FILE_SIZE_MB}MB"
                    )
                data = base64.b64encode(bytes).decode("utf-8")
                if data[0] == "A":
                    mime = "video/mp4"
                elif data[0] == "G":
                    mime = "video/webm"
                elif data[0] == "T":
                    mime = "video/ogg"
                elif data[0] == "U":
                    mime = "video/avi"
                else:
                    mime = "video/mp4"
                url = f"data:{mime};base64,{data}"
            c = Component(
                method_name="DISPLAY_VIDEO",
                label=label,
                initial_props=DisplayVideoProps(
                    url=url,
                    alt=alt,
                    muted=muted,
                    loop=loop,
                    height=height if height is not None else size,
                    width=width if width is not None else size,
                ).dict(),
            )
            return IOPromise(c, renderer=self._renderer)

    @dataclass
    class Experimental:
        _renderer: ComponentRenderer

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
