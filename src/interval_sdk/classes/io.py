import asyncio
import base64
import sys
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import (
    Iterable,
    Mapping,
    Optional,
    Union,
    overload,
    TypeVar,
    Literal,
    Any,
    Callable,
    Awaitable,
)
from typing_extensions import Never
from urllib.parse import ParseResult, urlparse

from ..io_schema import (
    ButtonItem,
    ButtonItemModel,
    CurrencyCode,
    DeserializableRecordModel,
    DisplayGridProps,
    DisplayGridState,
    DisplayHeadingProps,
    DisplayTableState,
    FileState,
    FileUrlSet,
    GridItem,
    InputTextProps,
    InternalTableRow,
    SelectTableReturnModel,
    SelectTableState,
    InputEmailProps,
    InputNumberProps,
    InputBooleanProps,
    InputRichTextProps,
    InputUrlProps,
    DateModel,
    TableMenuItem,
    TimeModel,
    DateTimeModel,
    InputDateProps,
    InputTimeProps,
    InputDateTimeProps,
    TableColumnDef,
    InternalTableColumn,
    SelectTableProps,
    PassthroughRichSelectOption,
    RichSelectOption,
    SelectSingleProps,
    RichSelectOptionModel,
    SelectMultipleProps,
    PassthroughLabelValue,
    LabelValue,
    LabelValueModel,
    DisplayCodeProps,
    DisplayLinkProps,
    LinkTheme,
    MetadataLayout,
    DisplayMetadataProps,
    KeyValueObjectModel,
    DisplayObjectProps,
    ImageSize,
    DisplayImageProps,
    DisplayTableProps,
    DisplayVideoProps,
    TypeValue,
    InputSpreadsheetProps,
    ConfirmProps,
    ConfirmIdentityProps,
    MethodName,
    SearchProps,
    SearchState,
    PassthroughSearchResultValue,
    RenderableSearchResult,
    InnerRenderableSearchResultModel,
    UploadFileProps,
    UploadFileState,
    InnerFileModel,
)
from .io_promise import (
    DisplayIOPromise,
    IOGroupPromise,
    GroupableIOPromise,
    ExclusiveIOPromise,
    InputIOPromise,
    KeyedIONamespace,
    MultipleableIOPromise,
)
from .component import (
    Component,
    ComponentRenderer,
)
from .interval_file import IntervalFile
from ..components.table import (
    TR,
    TABLE_DATA_BUFFER_SIZE,
    FetchedTableData,
    TableDataFetcher,
    TableDataFetcherState,
    columns_builder,
    filter_rows,
    serialize_table_row,
    sort_rows,
)
from ..components.grid import (
    GI,
    FetchedGridData,
    GridDataFetcher,
    GridDataFetcherState,
    filter_items,
    serialize_grid_item,
)


from ..util import (
    DeserializableRecord,
    KeyValueObject,
    ObjectLiteral,
    SerializableRecord,
)


_T1 = TypeVar("_T1")
_T2 = TypeVar("_T2")
_T3 = TypeVar("_T3")
_T4 = TypeVar("_T4")
_T5 = TypeVar("_T5")
_T6 = TypeVar("_T6")
_T7 = TypeVar("_T7")
_T8 = TypeVar("_T8")
_T9 = TypeVar("_T9")

MAX_FILE_SIZE_MB = 50


class IO:
    @dataclass
    class Input:
        _renderer: ComponentRenderer

        def text(
            self,
            label: str,
            *,
            help_text: Optional[str] = None,
            default_value: Optional[str] = None,
            multiline: Optional[bool] = None,
            lines: Optional[int] = None,
            disabled: Optional[bool] = None,
            placeholder: Optional[str] = None,
            min_length: Optional[int] = None,
            max_length: Optional[int] = None,
        ) -> InputIOPromise[Literal["INPUT_TEXT"], str]:
            c = Component(
                method_name="INPUT_TEXT",
                label=label,
                initial_props=InputTextProps(
                    help_text=help_text,
                    default_value=default_value,
                    multiline=multiline,
                    lines=lines,
                    disabled=disabled,
                    placeholder=placeholder,
                    min_length=min_length,
                    max_length=max_length,
                ),
            )
            return InputIOPromise(c, renderer=self._renderer)

        def email(
            self,
            label: str,
            *,
            help_text: Optional[str] = None,
            default_value: Optional[str] = None,
            disabled: Optional[bool] = None,
            placeholder: Optional[str] = None,
        ) -> InputIOPromise[Literal["INPUT_EMAIL"], str]:
            c = Component(
                method_name="INPUT_EMAIL",
                label=label,
                initial_props=InputEmailProps(
                    help_text=help_text,
                    default_value=default_value,
                    disabled=disabled,
                    placeholder=placeholder,
                ),
            )
            return InputIOPromise(c, renderer=self._renderer)

        @overload
        def number(
            self,
            label: str,
            *,
            min: Optional[Union[float, int]] = None,
            max: Optional[Union[float, int]] = None,
            prepend: Optional[str] = None,
            help_text: Optional[str] = None,
            default_value: Optional[Union[float, int]] = None,
            decimals: None = None,
            disabled: Optional[bool] = None,
            placeholder: Optional[str] = None,
            currency: Optional[CurrencyCode] = None,
        ) -> InputIOPromise[Literal["INPUT_NUMBER"], int]:
            ...

        @overload
        def number(
            self,
            label: str,
            *,
            min: Optional[Union[float, int]] = None,
            max: Optional[Union[float, int]] = None,
            prepend: Optional[str] = None,
            help_text: Optional[str] = None,
            default_value: Optional[Union[float, int]] = None,
            decimals: int = 0,
            disabled: Optional[bool] = None,
            placeholder: Optional[str] = None,
            currency: Optional[CurrencyCode] = None,
        ) -> InputIOPromise[Literal["INPUT_NUMBER"], float]:
            ...

        def number(
            self,
            label: str,
            *,
            min: Optional[Union[float, int]] = None,
            max: Optional[Union[float, int]] = None,
            prepend: Optional[str] = None,
            help_text: Optional[str] = None,
            default_value: Optional[Union[float, int]] = None,
            decimals: Optional[int] = None,
            disabled: Optional[bool] = None,
            placeholder: Optional[str] = None,
            currency: Optional[CurrencyCode] = None,
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
                    disabled=disabled,
                    placeholder=placeholder,
                    currency=currency,
                ),
            )

            def get_value(val: float):
                if decimals is None:
                    return int(val)

                return val

            return InputIOPromise(c, renderer=self._renderer, get_value=get_value)

        def boolean(
            self,
            label: str,
            *,
            help_text: Optional[str] = None,
            default_value: Optional[str] = None,
            disabled: Optional[bool] = None,
        ) -> InputIOPromise[Literal["INPUT_BOOLEAN"], bool]:
            c = Component(
                method_name="INPUT_BOOLEAN",
                label=label,
                initial_props=InputBooleanProps(
                    help_text=help_text,
                    default_value=default_value,
                    disabled=disabled,
                ),
            )
            return InputIOPromise(c, renderer=self._renderer)

        def rich_text(
            self,
            label: str,
            *,
            help_text: Optional[str] = None,
            disabled: Optional[bool] = None,
            placeholder: Optional[str] = None,
            default_value: Optional[str] = None,
        ) -> InputIOPromise[Literal["INPUT_RICH_TEXT"], str]:
            c = Component(
                method_name="INPUT_RICH_TEXT",
                label=label,
                initial_props=InputRichTextProps(
                    help_text=help_text,
                    disabled=disabled,
                    placeholder=placeholder,
                    default_value=default_value,
                ),
            )
            return InputIOPromise(c, renderer=self._renderer)

        def url(
            self,
            label: str,
            *,
            help_text: Optional[str] = None,
            allowed_protocols: Optional[Iterable[str]] = None,
            default_value: Optional[str] = None,
            disabled: Optional[bool] = None,
            placeholder: Optional[str] = None,
        ) -> InputIOPromise[Literal["INPUT_URL"], ParseResult]:
            c = Component(
                method_name="INPUT_URL",
                label=label,
                initial_props=InputUrlProps(
                    help_text=help_text,
                    allowed_protocols=[*allowed_protocols]
                    if allowed_protocols is not None
                    and not isinstance(allowed_protocols, list)
                    else allowed_protocols,
                    default_value=default_value,
                    disabled=disabled,
                    placeholder=placeholder,
                ),
            )

            def get_value(val: Any) -> ParseResult:
                return urlparse(val)

            return InputIOPromise(c, renderer=self._renderer, get_value=get_value)

        def date(
            self,
            label: str,
            *,
            help_text: Optional[str] = None,
            default_value: Optional[date] = None,
            disabled: Optional[bool] = None,
            min: Optional[date] = None,
            max: Optional[date] = None,
        ) -> InputIOPromise[Literal["INPUT_DATE"], date]:
            c = Component(
                method_name="INPUT_DATE",
                label=label,
                initial_props=InputDateProps(
                    help_text=help_text,
                    default_value=DateModel(
                        year=default_value.year,
                        month=default_value.month,
                        day=default_value.day,
                    )
                    if default_value is not None
                    else None,
                    disabled=disabled,
                    min=DateModel(
                        year=min.year,
                        month=min.month,
                        day=min.day,
                    )
                    if min is not None
                    else None,
                    max=DateModel(
                        year=max.year,
                        month=max.month,
                        day=max.day,
                    )
                    if max is not None
                    else None,
                ),
            )

            def get_value(val: DateModel) -> date:
                return date(val.year, val.month, val.day)

            return InputIOPromise(c, renderer=self._renderer, get_value=get_value)

        def time(
            self,
            label: str,
            *,
            help_text: Optional[str] = None,
            default_value: Optional[time] = None,
            disabled: Optional[bool] = None,
            min: Optional[time] = None,
            max: Optional[time] = None,
        ) -> InputIOPromise[Literal["INPUT_TIME"], time]:
            c = Component(
                method_name="INPUT_TIME",
                label=label,
                initial_props=InputTimeProps(
                    help_text=help_text,
                    default_value=TimeModel(
                        hour=default_value.hour, minute=default_value.minute
                    )
                    if default_value is not None
                    else None,
                    disabled=disabled,
                    min=TimeModel(hour=min.hour, minute=min.minute)
                    if min is not None
                    else None,
                    max=TimeModel(hour=max.hour, minute=max.minute)
                    if max is not None
                    else None,
                ),
            )

            def get_value(val: TimeModel) -> time:
                return time(val.hour, val.minute)

            return InputIOPromise(c, renderer=self._renderer, get_value=get_value)

        def datetime(
            self,
            label: str,
            *,
            help_text: Optional[str] = None,
            default_value: Optional[datetime] = None,
            disabled: Optional[bool] = None,
            min: Optional[datetime] = None,
            max: Optional[datetime] = None,
        ) -> InputIOPromise[Literal["INPUT_DATETIME"], datetime]:
            c = Component(
                method_name="INPUT_DATETIME",
                label=label,
                initial_props=InputDateTimeProps(
                    help_text=help_text,
                    default_value=DateTimeModel(
                        year=default_value.year,
                        month=default_value.month,
                        day=default_value.day,
                        hour=default_value.hour,
                        minute=default_value.minute,
                    )
                    if default_value is not None
                    else None,
                    disabled=disabled,
                    min=DateTimeModel(
                        year=min.year,
                        month=min.month,
                        day=min.day,
                        hour=min.hour,
                        minute=min.minute,
                    )
                    if min is not None
                    else None,
                    max=DateTimeModel(
                        year=max.year,
                        month=max.month,
                        day=max.day,
                        hour=max.hour,
                        minute=max.minute,
                    )
                    if max is not None
                    else None,
                ),
            )

            def get_value(val: DateTimeModel) -> datetime:
                return datetime(val.year, val.month, val.day, val.hour, val.minute)

            return InputIOPromise(c, renderer=self._renderer, get_value=get_value)

        def file(
            self,
            label: str,
            *,
            allowed_extensions: Optional[Iterable[str]] = None,
            help_text: Optional[str] = None,
            generate_presigned_urls: Optional[
                Callable[
                    [FileState],
                    Awaitable[FileUrlSet],
                ]
            ] = None,
            disabled: Optional[bool] = None,
        ) -> MultipleableIOPromise[Literal["UPLOAD_FILE"], IntervalFile, Never]:
            async def handle_state_change(
                state: UploadFileState, props: UploadFileProps
            ) -> UploadFileProps:
                if generate_presigned_urls is None:
                    props.file_urls = None
                    return props

                props.file_urls = await asyncio.gather(
                    *(generate_presigned_urls(file) for file in state.files)
                )
                return props

            c = Component(
                method_name="UPLOAD_FILE",
                label=label,
                initial_props=UploadFileProps(
                    help_text=help_text,
                    allowed_extensions=[*allowed_extensions]
                    if allowed_extensions is not None
                    and not isinstance(allowed_extensions, list)
                    else allowed_extensions,
                    disabled=disabled,
                    file_urls=[],
                ),
                handle_state_change=handle_state_change,
            )

            def get_value(val: InnerFileModel) -> IntervalFile:
                return IntervalFile(
                    last_modified=val.last_modified,
                    name=val.name,
                    size=val.size,
                    type=val.type,
                    url=val.url,
                )

            return MultipleableIOPromise(
                c, renderer=self._renderer, get_value=get_value
            )

    @dataclass
    class Select:
        _renderer: ComponentRenderer

        def table(
            self,
            label: str,
            *,
            data: Iterable[TR],
            row_menu_items: Optional[Callable[[TR], Iterable[TableMenuItem]]] = None,
            help_text: Optional[str] = None,
            columns: Optional[Iterable[Union[TableColumnDef, str]]] = None,
            min_selections: Optional[int] = None,
            max_selections: Optional[int] = None,
            disabled: Optional[bool] = None,
            default_page_size: Optional[int] = None,
            is_sortable: bool = True,
            is_filterable: bool = True,
        ) -> InputIOPromise[Literal["SELECT_TABLE"], list[TR]]:
            normalized_columns = columns_builder(data=data, columns=columns)
            serialized_rows = [
                serialize_table_row(
                    key=str(i),
                    row=row,
                    columns=normalized_columns,
                    menu_builder=row_menu_items,
                )
                for (i, row) in enumerate(data)
            ]

            async def handle_state_change(
                state: SelectTableState,
                props: SelectTableProps,
            ) -> SelectTableProps:
                new_sorted: list[InternalTableRow] = sort_rows(
                    filter_rows(serialized_rows, state.query_term),
                    state.sort_column,
                    state.sort_direction,
                )

                selected_keys = []

                if state.is_select_all:
                    selected_keys = [row.key for row in new_sorted]

                props.data = [
                    InternalTableRow.revalidate(row)
                    for row in new_sorted[
                        state.offset : state.offset
                        + min(state.page_size * 3, TABLE_DATA_BUFFER_SIZE)
                    ]
                ]
                props.selected_keys = selected_keys
                props.total_records = len(new_sorted)

                return props

            c = Component(
                method_name="SELECT_TABLE",
                label=label,
                initial_props=SelectTableProps(
                    help_text=help_text,
                    columns=[
                        InternalTableColumn.parse_obj(col) for col in normalized_columns
                    ],
                    data=[
                        InternalTableRow.revalidate(row)
                        for row in serialized_rows[:TABLE_DATA_BUFFER_SIZE]
                    ],
                    min_selections=min_selections,
                    max_selections=max_selections,
                    total_records=len(serialized_rows),
                    disabled=disabled,
                    default_page_size=default_page_size,
                    is_sortable=is_sortable,
                    is_filterable=is_filterable,
                ),
                handle_state_change=handle_state_change,
            )

            def get_value(val: list[SelectTableReturnModel]) -> list[TR]:
                indices = [int(row.key) for row in val]
                rows = [row for (i, row) in enumerate(data) if i in indices]
                return rows

            return InputIOPromise(c, renderer=self._renderer, get_value=get_value)

        @overload
        def single(
            self,
            label: str,
            *,
            options: Iterable[PassthroughRichSelectOption],
            help_text: Optional[str] = None,
            default_value: Optional[Union[RichSelectOption, ObjectLiteral]] = None,
            searchable: Optional[bool] = None,
            disabled: Optional[bool] = None,
        ) -> InputIOPromise[Literal["SELECT_SINGLE"], PassthroughRichSelectOption]:
            ...

        @overload
        def single(
            self,
            label: str,
            *,
            options: Iterable[RichSelectOption],
            help_text: Optional[str] = None,
            default_value: Optional[RichSelectOption] = None,
            searchable: Optional[bool] = None,
            disabled: Optional[bool] = None,
        ) -> InputIOPromise[Literal["SELECT_SINGLE"], RichSelectOption]:
            ...

        @overload
        def single(
            self,
            label: str,
            *,
            options: Iterable[ObjectLiteral],
            help_text: Optional[str] = None,
            default_value: Optional[ObjectLiteral] = None,
            searchable: Optional[bool] = None,
            disabled: Optional[bool] = None,
        ) -> InputIOPromise[Literal["SELECT_SINGLE"], ObjectLiteral]:
            ...

        @overload
        def single(
            self,
            label: str,
            *,
            options: Iterable[Union[RichSelectOption, ObjectLiteral]],
            help_text: Optional[str] = None,
            default_value: Optional[Union[RichSelectOption, ObjectLiteral]] = None,
            searchable: Optional[bool] = None,
            disabled: Optional[bool] = None,
        ) -> InputIOPromise[
            Literal["SELECT_SINGLE"], Union[RichSelectOption, ObjectLiteral]
        ]:
            ...

        def single(
            self,
            label: str,
            *,
            options: Iterable[PassthroughRichSelectOption],
            help_text: Optional[str] = None,
            default_value: Optional[Union[RichSelectOption, ObjectLiteral]] = None,
            searchable: Optional[bool] = None,
            disabled: Optional[bool] = None,
        ) -> InputIOPromise[Literal["SELECT_SINGLE"], PassthroughRichSelectOption]:
            normalized_options: list[RichSelectOption] = [
                {"label": option, "value": option}
                if isinstance(option, (str, int, bool, float, date, time, datetime))
                or option is None
                else option
                for option in options
            ]
            normalized_default_value: Optional[RichSelectOption] = (
                {"label": default_value, "value": default_value}
                if isinstance(
                    default_value, (str, int, bool, float, date, time, datetime)
                )
                else default_value
            )

            c = Component(
                method_name="SELECT_SINGLE",
                label=label,
                initial_props=SelectSingleProps(
                    options=[
                        RichSelectOptionModel.parse_obj(option)
                        for option in normalized_options
                    ],
                    help_text=help_text,
                    default_value=RichSelectOptionModel.parse_obj(
                        normalized_default_value
                    )
                    if normalized_default_value is not None
                    else None,
                    searchable=searchable,
                    disabled=disabled,
                ),
            )
            option_map = {
                option
                if isinstance(option, (str, int, bool, float, date, time, datetime))
                or option is None
                else option["value"]: option
                for option in options
            }

            def get_value(
                item: RichSelectOptionModel,
            ) -> PassthroughRichSelectOption:
                return option_map[item.value]

            return InputIOPromise(c, renderer=self._renderer, get_value=get_value)

        @overload
        def multiple(
            self,
            label: str,
            *,
            options: Iterable[PassthroughLabelValue],
            help_text: Optional[str] = None,
            default_value: Optional[Iterable[Union[LabelValue, ObjectLiteral]]] = None,
            min_selections: Optional[int] = None,
            max_selections: Optional[int] = None,
            disabled: Optional[bool] = None,
        ) -> InputIOPromise[Literal["SELECT_MULTIPLE"], list[PassthroughLabelValue]]:
            ...

        @overload
        def multiple(
            self,
            label: str,
            *,
            options: Iterable[LabelValue],
            help_text: Optional[str] = None,
            default_value: Optional[Iterable[LabelValue]] = None,
            min_selections: Optional[int] = None,
            max_selections: Optional[int] = None,
            disabled: Optional[bool] = None,
        ) -> InputIOPromise[Literal["SELECT_MULTIPLE"], list[LabelValue]]:
            ...

        @overload
        def multiple(
            self,
            label: str,
            *,
            options: Iterable[ObjectLiteral],
            help_text: Optional[str] = None,
            default_value: Optional[Iterable[ObjectLiteral]] = None,
            min_selections: Optional[int] = None,
            max_selections: Optional[int] = None,
            disabled: Optional[bool] = None,
        ) -> InputIOPromise[Literal["SELECT_MULTIPLE"], list[ObjectLiteral]]:
            ...

        @overload
        def multiple(
            self,
            label: str,
            *,
            options: Iterable[Union[LabelValue, ObjectLiteral]],
            help_text: Optional[str] = None,
            default_value: Optional[Iterable[Union[LabelValue, ObjectLiteral]]] = None,
            min_selections: Optional[int] = None,
            max_selections: Optional[int] = None,
            disabled: Optional[bool] = None,
        ) -> InputIOPromise[
            Literal["SELECT_MULTIPLE"], list[Union[LabelValue, ObjectLiteral]]
        ]:
            ...

        def multiple(
            self,
            label: str,
            *,
            options: Iterable[PassthroughLabelValue],
            help_text: Optional[str] = None,
            default_value: Optional[Iterable[Union[LabelValue, ObjectLiteral]]] = None,
            min_selections: Optional[int] = None,
            max_selections: Optional[int] = None,
            disabled: Optional[bool] = None,
        ) -> InputIOPromise[Literal["SELECT_MULTIPLE"], list[PassthroughLabelValue]]:
            normalized_options: list[LabelValue] = [
                {"label": option, "value": option}
                if isinstance(option, (str, int, bool, float, date, time, datetime))
                or option is None
                else option
                for option in options
            ]
            normalized_default_value: Optional[list[LabelValue]] = (
                [
                    {"label": value, "value": value}
                    if isinstance(value, (str, int, bool, float, date, time, datetime))
                    or value is None
                    else value
                    for value in default_value
                ]
                if default_value is not None
                else default_value
            )

            c = Component(
                method_name="SELECT_MULTIPLE",
                label=label,
                initial_props=SelectMultipleProps(
                    options=[
                        LabelValueModel.parse_obj(option)
                        for option in normalized_options
                    ],
                    help_text=help_text,
                    default_value=[
                        LabelValueModel.parse_obj(val)
                        for val in normalized_default_value
                    ]
                    if normalized_default_value is not None
                    else [],
                    min_selections=min_selections,
                    max_selections=max_selections,
                    disabled=disabled,
                ),
            )

            option_map = {
                option
                if isinstance(option, (str, int, bool, float, date, time, datetime))
                or option is None
                else option["value"]: option
                for option in options
            }

            def get_value(
                val: list[LabelValueModel],
            ) -> list[PassthroughLabelValue]:
                return [option_map[item.value] for item in val]

            return InputIOPromise(c, renderer=self._renderer, get_value=get_value)

    @dataclass
    class Display:
        _renderer: ComponentRenderer

        def code(
            self,
            label: str,
            *,
            code: str,
            language: Optional[str] = None,
        ) -> DisplayIOPromise[Literal["DISPLAY_CODE"], None]:
            c = Component(
                method_name="DISPLAY_CODE",
                label=label,
                initial_props=DisplayCodeProps(
                    code=code,
                    language=language,
                ),
            )
            return DisplayIOPromise(c, renderer=self._renderer)

        def heading(
            self,
            label: str,
            *,
            level: Optional[Literal[2, 3, 4]] = None,
            description: Optional[str] = None,
            menu_items: Optional[Iterable[ButtonItem]] = None,
        ) -> DisplayIOPromise[Literal["DISPLAY_HEADING"], None]:
            c = Component(
                method_name="DISPLAY_HEADING",
                label=label,
                initial_props=DisplayHeadingProps(
                    level=level,
                    description=description,
                    menu_items=[ButtonItemModel.parse_obj(i) for i in menu_items]
                    if menu_items is not None
                    else None,
                ),
            )
            return DisplayIOPromise(c, renderer=self._renderer)

        def link(
            self,
            label: str,
            *,
            route: Optional[str] = None,
            params: Optional[SerializableRecord] = None,
            theme: LinkTheme = "default",
            url: Optional[str] = None,
        ) -> DisplayIOPromise[Literal["DISPLAY_LINK"], None]:
            c = Component(
                method_name="DISPLAY_LINK",
                label=label,
                initial_props=DisplayLinkProps(
                    route=route,
                    params=params,
                    theme=theme,
                    url=url,
                ),
            )
            return DisplayIOPromise(c, renderer=self._renderer)

        def markdown(
            self,
            label: str,
        ) -> DisplayIOPromise[Literal["DISPLAY_MARKDOWN"], None]:
            c = Component(
                method_name="DISPLAY_MARKDOWN",
                label=label,
                initial_props=None,
            )
            return DisplayIOPromise(c, renderer=self._renderer)

        def metadata(
            self,
            label: str,
            *,
            data: KeyValueObject,
            layout: MetadataLayout = "grid",
        ) -> DisplayIOPromise[Literal["DISPLAY_METADATA"], None]:
            c = Component(
                method_name="DISPLAY_METADATA",
                label=label,
                initial_props=DisplayMetadataProps(
                    layout=layout,
                    data=KeyValueObjectModel.parse_obj(data),
                ),
            )
            return DisplayIOPromise(c, renderer=self._renderer)

        def object(
            self,
            label: str,
            *,
            data: KeyValueObject,
        ) -> DisplayIOPromise[Literal["DISPLAY_OBJECT"], None]:
            c = Component(
                method_name="DISPLAY_OBJECT",
                label=label,
                initial_props=DisplayObjectProps(
                    data=KeyValueObjectModel.parse_obj(data),
                ),
            )
            return DisplayIOPromise(c, renderer=self._renderer)

        def image(
            self,
            label: str,
            *,
            url: Optional[str] = None,
            bytes: Optional[bytes] = None,
            alt: Optional[str] = None,
            size: Optional[ImageSize] = None,
        ) -> DisplayIOPromise[Literal["DISPLAY_IMAGE"], None]:
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
                    height=size,
                    width=size,
                ),
            )
            return DisplayIOPromise(c, renderer=self._renderer)

        @overload
        def table(
            self,
            label: str,
            *,
            data: Iterable[TR],
            get_data: Optional[TableDataFetcher] = None,
            row_menu_items: Optional[Callable[[TR], Iterable[TableMenuItem]]] = None,
            help_text: Optional[str] = None,
            columns: Optional[Iterable[Union[TableColumnDef, str]]] = None,
            default_page_size: Optional[int] = None,
            is_sortable: bool = True,
            is_filterable: bool = True,
        ) -> DisplayIOPromise[Literal["DISPLAY_TABLE"], None]:
            ...

        @overload
        def table(
            self,
            label: str,
            *,
            data: Optional[Iterable[TR]] = None,
            get_data: TableDataFetcher,
            row_menu_items: Optional[Callable[[TR], Iterable[TableMenuItem]]] = None,
            help_text: Optional[str] = None,
            columns: Optional[Iterable[Union[TableColumnDef, str]]] = None,
            default_page_size: Optional[int] = None,
            is_sortable: bool = True,
            is_filterable: bool = True,
        ) -> DisplayIOPromise[Literal["DISPLAY_TABLE"], None]:
            ...

        def table(
            self,
            label: str,
            *,
            data: Optional[Iterable[TR]] = None,
            get_data: Optional[TableDataFetcher] = None,
            row_menu_items: Optional[Callable[[TR], Iterable[TableMenuItem]]] = None,
            help_text: Optional[str] = None,
            columns: Optional[Iterable[Union[TableColumnDef, str]]] = None,
            default_page_size: Optional[int] = None,
            is_sortable: bool = True,
            is_filterable: bool = True,
        ) -> DisplayIOPromise[Literal["DISPLAY_TABLE"], None]:
            normalized_columns = columns_builder(data=data, columns=columns)
            serialized_rows = (
                [
                    serialize_table_row(
                        key=str(i),
                        row=row,
                        columns=normalized_columns,
                        menu_builder=row_menu_items,
                    )
                    for (i, row) in enumerate(data)
                ]
                if data is not None
                else []
            )

            async def handle_state_change(
                state: DisplayTableState,
                props: DisplayTableProps,
            ) -> DisplayTableProps:
                if get_data is not None:
                    fetched = await get_data(TableDataFetcherState(**state.dict()))
                    if isinstance(fetched, list):
                        fetched = FetchedTableData(fetched)
                    elif isinstance(fetched, tuple):
                        fetched = FetchedTableData(*fetched)

                    built_columns = columns_builder(data=fetched.data, columns=columns)
                    props.data = [
                        InternalTableRow.revalidate(
                            serialize_table_row(
                                key=str(i + state.offset),
                                row=row,
                                columns=built_columns,
                                menu_builder=row_menu_items,
                            )
                        )
                        for (i, row) in enumerate(fetched.data)
                    ]
                    props.columns = [
                        InternalTableColumn.parse_obj(col) for col in built_columns
                    ]
                    if fetched.total_records is not None:
                        props.total_records = fetched.total_records
                else:
                    new_sorted: list[InternalTableRow] = sort_rows(
                        filter_rows(serialized_rows, state.query_term),
                        state.sort_column,
                        state.sort_direction,
                    )
                    props.data = [
                        InternalTableRow.revalidate(row)
                        for row in new_sorted[
                            state.offset : state.offset
                            + min(state.page_size * 3, TABLE_DATA_BUFFER_SIZE)
                        ]
                    ]
                    props.total_records = len(new_sorted)

                return props

            c = Component(
                method_name="DISPLAY_TABLE",
                label=label,
                initial_props=DisplayTableProps(
                    help_text=help_text,
                    columns=[
                        InternalTableColumn.parse_obj(col) for col in normalized_columns
                    ],
                    data=[
                        InternalTableRow.revalidate(row)
                        for row in serialized_rows[:TABLE_DATA_BUFFER_SIZE]
                    ],
                    total_records=len(serialized_rows) if data is not None else None,
                    default_page_size=default_page_size,
                    is_sortable=is_sortable,
                    is_filterable=is_filterable,
                    is_async=get_data is not None,
                ),
                handle_state_change=handle_state_change,
            )
            return DisplayIOPromise(c, renderer=self._renderer)

        @overload
        def grid(
            self,
            label: str,
            *,
            data: Iterable[GI],
            get_data: Optional[GridDataFetcher] = None,
            render_item: Callable[[GI], GridItem],
            help_text: Optional[str] = None,
            ideal_column_width: Optional[int] = None,
            default_page_size: Optional[int] = None,
            is_filterable: bool = True,
        ) -> DisplayIOPromise[Literal["DISPLAY_GRID"], None]:
            ...

        @overload
        def grid(
            self,
            label: str,
            *,
            data: Optional[Iterable[GI]] = None,
            get_data: GridDataFetcher,
            render_item: Callable[[GI], GridItem],
            help_text: Optional[str] = None,
            ideal_column_width: Optional[int] = None,
            default_page_size: Optional[int] = None,
            is_filterable: bool = True,
        ) -> DisplayIOPromise[Literal["DISPLAY_GRID"], None]:
            ...

        def grid(
            self,
            label: str,
            *,
            data: Optional[Iterable[GI]] = None,
            get_data: Optional[GridDataFetcher] = None,
            render_item: Callable[[GI], GridItem],
            help_text: Optional[str] = None,
            ideal_column_width: Optional[int] = None,
            default_page_size: Optional[int] = None,
            is_filterable: bool = True,
        ) -> DisplayIOPromise[Literal["DISPLAY_GRID"], None]:
            serialized_items = (
                [
                    serialize_grid_item(key=str(i), item=item, render_item=render_item)
                    for (i, item) in enumerate(data)
                ]
                if data is not None
                else []
            )

            async def handle_state_change(
                state: DisplayGridState,
                props: DisplayGridProps,
            ) -> DisplayGridProps:
                if get_data is not None:
                    fetched = await get_data(GridDataFetcherState(**state.dict()))
                    if isinstance(fetched, list):
                        fetched = FetchedGridData(fetched)
                    elif isinstance(fetched, tuple):
                        fetched = FetchedGridData(*fetched)

                    props.data = [
                        serialize_grid_item(
                            key=str(i + state.offset),
                            item=item,
                            render_item=render_item,
                        )
                        for (i, item) in enumerate(fetched.data)
                    ]
                    if fetched.total_records is not None:
                        props.total_records = fetched.total_records
                else:
                    new_filtered = filter_items(serialized_items, state.query_term)
                    props.data = new_filtered[
                        state.offset : state.offset
                        + min(state.page_size * 3, TABLE_DATA_BUFFER_SIZE)
                    ]
                    props.total_records = len(new_filtered)

                return props

            c = Component(
                method_name="DISPLAY_GRID",
                label=label,
                initial_props=DisplayGridProps(
                    help_text=help_text,
                    data=serialized_items[:TABLE_DATA_BUFFER_SIZE],
                    default_page_size=default_page_size,
                    ideal_column_width=ideal_column_width,
                    is_filterable=is_filterable,
                    total_records=len(serialized_items) if data is not None else None,
                    is_async=get_data is not None,
                ),
                handle_state_change=handle_state_change,
            )
            return DisplayIOPromise(c, renderer=self._renderer)

        def video(
            self,
            label: str,
            *,
            url: Optional[str] = None,
            bytes: Optional[bytes] = None,
            loop: bool = False,
            muted: bool = False,
            size: Optional[ImageSize] = None,
            height: Optional[ImageSize] = None,
            width: Optional[ImageSize] = None,
        ) -> DisplayIOPromise[Literal["DISPLAY_VIDEO"], None]:
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
                    muted=muted,
                    loop=loop,
                    height=height if height is not None else size,
                    width=width if width is not None else size,
                ),
            )
            return DisplayIOPromise(c, renderer=self._renderer)

    @dataclass
    class Experimental:
        _renderer: ComponentRenderer

        def spreadsheet(
            self,
            label: str,
            columns: dict[str, TypeValue],
            help_text: Optional[str] = None,
            default_value: Optional[Iterable[DeserializableRecord]] = None,
        ) -> InputIOPromise[Literal["INPUT_SPREADSHEET"], list[SerializableRecord]]:
            c = Component(
                method_name="INPUT_SPREADSHEET",
                label=label,
                initial_props=InputSpreadsheetProps(
                    help_text=help_text,
                    columns=columns,
                    default_value=[
                        DeserializableRecordModel.parse_obj(v) for v in default_value
                    ]
                    if default_value is not None
                    else None,
                ),
            )
            return InputIOPromise(c, renderer=self._renderer)

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
        help_text: Optional[str] = None,
    ) -> ExclusiveIOPromise[Literal["CONFIRM"], bool]:
        c = Component(
            method_name="CONFIRM",
            label=label,
            initial_props=ConfirmProps(
                help_text=help_text,
            ),
        )
        return ExclusiveIOPromise(c, renderer=self._renderer)

    def confirm_identity(
        self,
        label: str,
        grace_period: Optional[float] = None,
    ) -> ExclusiveIOPromise[Literal["CONFIRM_IDENTITY"], bool]:
        c = Component(
            method_name="CONFIRM_IDENTITY",
            label=label,
            initial_props=ConfirmIdentityProps(
                grace_period_ms=int(grace_period * 1000)
                if grace_period is not None
                else None,
            ),
        )
        return ExclusiveIOPromise(c, renderer=self._renderer)

    # Based on typing for asyncio.gather
    # https://github.com/python/typeshed/blob/4d23919200d9e89486f4d9e2587f82314d4af0f6/stdlib/asyncio/tasks.pyi#L82-L165
    @overload
    def group(
        self,
        p1: GroupableIOPromise[MethodName, _T1],
    ) -> IOGroupPromise[_T1]:
        """
        Actually returns a list, claims to return a tuple because lists do not support
        variadic types.
        """

    @overload
    def group(
        self,
        p1: GroupableIOPromise[MethodName, _T1],
        p2: GroupableIOPromise[MethodName, _T2],
    ) -> IOGroupPromise[_T1, _T2]:
        ...

    @overload
    def group(
        self,
        p1: GroupableIOPromise[MethodName, _T1],
        p2: GroupableIOPromise[MethodName, _T2],
        p3: GroupableIOPromise[MethodName, _T3],
    ) -> IOGroupPromise[_T1, _T2, _T3]:
        ...

    @overload
    def group(
        self,
        p1: GroupableIOPromise[MethodName, _T1],
        p2: GroupableIOPromise[MethodName, _T2],
        p3: GroupableIOPromise[MethodName, _T3],
        p4: GroupableIOPromise[MethodName, _T4],
    ) -> IOGroupPromise[_T1, _T2, _T3, _T4]:
        ...

    @overload
    def group(
        self,
        p1: GroupableIOPromise[MethodName, _T1],
        p2: GroupableIOPromise[MethodName, _T2],
        p3: GroupableIOPromise[MethodName, _T3],
        p4: GroupableIOPromise[MethodName, _T4],
        p5: GroupableIOPromise[MethodName, _T5],
        p6: GroupableIOPromise[MethodName, _T6],
    ) -> IOGroupPromise[_T1, _T2, _T3, _T4, _T5, _T6]:
        ...

    @overload
    def group(
        self,
        p1: GroupableIOPromise[MethodName, _T1],
        p2: GroupableIOPromise[MethodName, _T2],
        p3: GroupableIOPromise[MethodName, _T3],
        p4: GroupableIOPromise[MethodName, _T4],
        p5: GroupableIOPromise[MethodName, _T5],
        p6: GroupableIOPromise[MethodName, _T6],
        p7: GroupableIOPromise[MethodName, _T7],
    ) -> IOGroupPromise[_T1, _T2, _T3, _T4, _T5, _T6, _T7]:
        ...

    @overload
    def group(
        self,
        p1: GroupableIOPromise[MethodName, _T1],
        p2: GroupableIOPromise[MethodName, _T2],
        p3: GroupableIOPromise[MethodName, _T3],
        p4: GroupableIOPromise[MethodName, _T4],
        p5: GroupableIOPromise[MethodName, _T5],
        p6: GroupableIOPromise[MethodName, _T6],
        p7: GroupableIOPromise[MethodName, _T7],
        p8: GroupableIOPromise[MethodName, _T8],
    ) -> IOGroupPromise[_T1, _T2, _T3, _T4, _T5, _T6, _T7, _T8]:
        ...

    @overload
    def group(
        self,
        p1: GroupableIOPromise[MethodName, _T1],
        p2: GroupableIOPromise[MethodName, _T2],
        p3: GroupableIOPromise[MethodName, _T3],
        p4: GroupableIOPromise[MethodName, _T4],
        p5: GroupableIOPromise[MethodName, _T5],
        p6: GroupableIOPromise[MethodName, _T6],
        p7: GroupableIOPromise[MethodName, _T7],
        p8: GroupableIOPromise[MethodName, _T8],
        p9: GroupableIOPromise[MethodName, _T9],
    ) -> IOGroupPromise[_T1, _T2, _T3, _T4, _T5, _T6, _T7, _T8, _T9]:
        ...

    @overload
    def group(
        self, *io_promises: GroupableIOPromise[MethodName, Any]
    ) -> IOGroupPromise[list[Any]]:
        ...

    @overload
    def group(
        self,
        **kw_io_promises: GroupableIOPromise[MethodName, Any],
    ) -> IOGroupPromise[KeyedIONamespace]:
        ...

    def group(  # type: ignore
        self,
        *io_promises: GroupableIOPromise[MethodName, Any],
        **kw_io_promises: GroupableIOPromise[MethodName, Any],
    ):
        return IOGroupPromise(
            renderer=self._renderer,
            io_promises=io_promises,
            kw_io_promises=kw_io_promises,
        )

    def search(
        self,
        label: str,
        *,
        on_search: Callable[
            [str],
            Awaitable[Iterable[PassthroughSearchResultValue]],
        ],
        render_result: Callable[
            [PassthroughSearchResultValue],
            Union[RenderableSearchResult, ObjectLiteral],
        ],
        help_text: Optional[str] = None,
        initial_results: Optional[Iterable[PassthroughSearchResultValue]] = None,
        default_value: Optional[PassthroughSearchResultValue] = None,
        disabled: Optional[bool] = None,
        placeholder: Optional[str] = None,
    ) -> MultipleableIOPromise[
        Literal["SEARCH"], PassthroughSearchResultValue, PassthroughSearchResultValue
    ]:
        if initial_results is None:
            initial_results = []

        result_batch_index: int = 0
        result_map: dict[str, list[PassthroughSearchResultValue]] = {
            "0": list(initial_results)
        }

        def render_result_wrapper(
            result: PassthroughSearchResultValue,
            index: int,
        ) -> InnerRenderableSearchResultModel:
            r = render_result(result)
            value = f"{len(result_map) - 1}:{index}"

            if isinstance(r, Mapping):
                return InnerRenderableSearchResultModel.parse_obj(
                    {
                        **r,
                        "value": value,
                    }
                )

            return InnerRenderableSearchResultModel(value=value, label=str(r))

        def render_results(results: Iterable[PassthroughSearchResultValue]):
            return [render_result_wrapper(r, i) for i, r in enumerate(results)]

        results = render_results(initial_results)

        def get_default_value(default_value: PassthroughSearchResultValue) -> str:
            nonlocal results

            if "default" not in result_map:
                result_map["default"] = []

            r = render_result(default_value)
            value = f"default:{len(result_map['default'])}"
            result_map["default"].append(default_value)

            if isinstance(r, Mapping):
                results.append(
                    InnerRenderableSearchResultModel.parse_obj({**r, "value": value})
                )
            else:
                results.append(
                    InnerRenderableSearchResultModel(value=value, label=str(r))
                )

            return value

        async def handle_state_change(
            state: SearchState, props: SearchProps
        ) -> SearchProps:
            nonlocal result_batch_index
            results = await on_search(state.query_term)
            if not isinstance(results, list):
                results = list(results)

            result_batch_index += 1
            result_map[str(result_batch_index)] = results

            props.results = render_results(results)
            return props

        c = Component(
            method_name="SEARCH",
            label=label,
            initial_props=SearchProps(
                help_text=help_text,
                results=results,
                disabled=disabled,
                placeholder=placeholder,
                default_value=get_default_value(default_value)
                if default_value is not None
                else None,
            ),
            handle_state_change=handle_state_change,
        )

        # Reassign this here so get_default_value modifies the working results list
        # Pydantic models seem to create new lists instead of referencing originals
        results = c.instance.props.results

        def get_value(val: str):
            batch_index, index = val.split(":")

            try:
                batch = result_map[batch_index]
                return batch[int(index)]
            except KeyError as err:
                raise ValueError("BAD_RESPONSE") from err

        return MultipleableIOPromise(
            c,
            renderer=self._renderer,
            get_value=get_value,
            get_default_value=get_default_value,
        )
