from __future__ import annotations
from dataclasses import dataclass
import traceback
from typing import (
    Union,
    cast,
    Any,
    Callable,
    Optional,
    Literal,
    Generic,
    TypeVar,
    Mapping,
    Type,
)
from datetime import date, time, datetime
from uuid import UUID
import io, json, sys
from typing_extensions import NotRequired, TypedDict, TypeAlias, override
from pydantic import (
    BaseModel as PydanticBaseModel,
    Field,
    PositiveInt,
    StrictBool,
    StrictInt,
    StrictFloat,
)
from pydantic.fields import ModelField

from .types import (
    BaseModel,
    GenericModel,
)
from .util import (
    ObjectLiteral,
    dict_strip_none,
    json_dumps_snake_strip_none,
    json_loads_snake_strip_none,
    snake_to_camel,
    dict_keys_to_camel,
    json_dumps_some_snake,
    json_loads_some_snake,
    Serializable,
    SerializableRecord,
)

# TODO: Try generating most of this with datamode-code-generator
# https://github.com/koxudaxi/datamodel-code-generator/

InputMethodName = Literal[
    "INPUT_TEXT",
    "INPUT_EMAIL",
    "INPUT_NUMBER",
    "INPUT_BOOLEAN",
    "INPUT_RICH_TEXT",
    "INPUT_SPREADSHEET",
    "INPUT_URL",
    "INPUT_DATE",
    "INPUT_TIME",
    "INPUT_DATETIME",
    "CONFIRM",
    "CONFIRM_IDENTITY",
    "SELECT_TABLE",
    "SELECT_SINGLE",
    "SELECT_MULTIPLE",
    "SEARCH",
    "UPLOAD_FILE",
]

MultipleableMethodName = Literal["SEARCH", "UPLOAD_FILE"]

DisplayMethodName = Literal[
    "DISPLAY_CODE",
    "DISPLAY_HEADING",
    "DISPLAY_IMAGE",
    "DISPLAY_LINK",
    "DISPLAY_MARKDOWN",
    "DISPLAY_METADATA",
    "DISPLAY_OBJECT",
    "DISPLAY_GRID",
    "DISPLAY_TABLE",
    "DISPLAY_VIDEO",
    "DISPLAY_PROGRESS_STEPS",
    "DISPLAY_PROGRESS_INDETERMINATE",
    "DISPLAY_PROGRESS_THROUGH_LIST",
]

MethodName = Union[InputMethodName, DisplayMethodName]

MN = TypeVar("MN", bound=MethodName)


class ComponentMultipleProps(BaseModel):
    defaultValue: Optional[list[Any]] = None


class ComponentRenderInfo(GenericModel, Generic[MN]):
    method_name: MN
    label: str
    props: Any
    is_stateful: bool
    is_optional: bool
    is_multiple: bool
    validation_error_message: Optional[str] = None
    multiple_props: Optional[ComponentMultipleProps] = None

    class Config:
        json_loads = json_loads_snake_strip_none
        json_dumps = json_dumps_snake_strip_none


TypeValue = Literal[
    "string",
    "string?",
    "number",
    "number?",
    "boolean",
    "boolean?",
]


ButtonTheme = Literal["primary", "secondary", "danger"]


class ButtonConfig(BaseModel):
    label: Optional[str] = None
    theme: Optional[ButtonTheme] = None


ImageSize: TypeAlias = Literal["thumbnail", "small", "medium", "large"]


class ImageDefinition(TypedDict):
    url: str
    alt: NotRequired[str]
    size: NotRequired[ImageSize]


class ImageDefinitionModel(BaseModel):
    url: str
    alt: Optional[str] = None
    size: Optional[ImageSize] = None


class RichSelectOption(TypedDict):
    label: ObjectLiteral
    value: ObjectLiteral
    description: NotRequired[str]
    image: NotRequired[ImageDefinition]


PassthroughRichSelectOption = TypeVar(
    "PassthroughRichSelectOption", bound=Union[RichSelectOption, ObjectLiteral]
)


class RichSelectOptionModel(BaseModel):
    label: ObjectLiteral
    value: ObjectLiteral
    description: Optional[str] = None
    image: Optional[ImageDefinitionModel] = None


class KeyValueObjectModel(BaseModel):
    __root__: Union[
        ObjectLiteral,
        list[Optional[KeyValueObjectModel]],
        dict[str, Optional[KeyValueObjectModel]],
    ]


class ImageSchema(TypedDict):
    url: NotRequired[str]
    alt: NotRequired[str]
    size: NotRequired[ImageSize]


class ImageModel(BaseModel):
    url: Optional[str] = None
    alt: Optional[str] = None
    size: Optional[ImageSize] = None


class ButtonItem(TypedDict):
    label: str
    theme: NotRequired[ButtonTheme]
    route: NotRequired[str]
    params: NotRequired[SerializableRecord]
    url: NotRequired[str]
    disabled: NotRequired[bool]


class ButtonItemModel(BaseModel):
    label: str
    theme: Optional[ButtonTheme] = None
    route: Optional[str] = None
    params: Optional[SerializableRecord] = None
    url: Optional[str] = None
    disabled: bool = False


class RenderableSearchResult(TypedDict):
    label: ObjectLiteral
    description: NotRequired[str]
    image: NotRequired[ImageSchema]


class RenderableSearchResultModel(BaseModel):
    label: ObjectLiteral
    description: Optional[str] = None
    image: Optional[ImageModel] = None


PassthroughRenderableSearchResult = TypeVar(
    "PassthroughRenderableSearchResult",
    bound=Union[RenderableSearchResult, ObjectLiteral],
)


class InnerRenderableSearchResultModel(RenderableSearchResultModel):
    value: str


class FileUrlSet(TypedDict):
    uploadUrl: str
    downloadUrl: str


class UploadFileProps(BaseModel):
    allowed_extensions: Optional[list[str]]
    help_text: Optional[str]
    disabled: Optional[bool]
    file_urls: Optional[list[FileUrlSet]]


@dataclass
class FileState:
    name: str
    type: str


class UploadFileState(BaseModel):
    files: list[FileState]


class InnerFileModel(BaseModel):
    last_modified: Optional[datetime] = None
    name: str
    type: str
    size: int
    url: str


KeyValueObjectModel.update_forward_refs()


class LabelValue(TypedDict):
    label: ObjectLiteral
    value: ObjectLiteral


PassthroughLabelValue = TypeVar(
    "PassthroughLabelValue", bound=Union[LabelValue, ObjectLiteral]
)


class LabelValueModel(BaseModel):
    label: ObjectLiteral
    value: ObjectLiteral


RawActionReturnData: TypeAlias = Mapping[str, Serializable]
IOFunctionReturnType: TypeAlias = Union[Serializable, SerializableRecord, None]


class ParsedActionReturnDataLink(BaseModel):
    data_kind: Optional[Literal["link"]]
    value: str


ParsedActionReturnDataValue = Union[SerializableRecord, ParsedActionReturnDataLink]

ParsedActionReturnData: TypeAlias = dict[str, ParsedActionReturnDataValue]


class DeserializableModel(BaseModel):
    __root__: Union[StrictInt, StrictFloat, StrictBool, None, str]


class DeserializableRecordModel(BaseModel):
    __root__: dict[str, Optional[DeserializableModel]]


class SerializableModel(BaseModel):
    __root__: Union[StrictInt, StrictFloat, StrictBool, None, date, time, datetime, str]


class SerializableRecordModel(BaseModel):
    __root__: dict[str, Optional[SerializableModel]]


class IOFunctionReturnModel(BaseModel):
    __root__: Union[DeserializableModel, DeserializableRecordModel, None]


class ActionResult(BaseModel):
    schema_version: Literal[0, 1] = 1
    status: Literal["SUCCESS", "FAILURE"]
    data: IOFunctionReturnModel

    class Config:
        json_dumps = json.dumps


TableRowValuePrimitive: TypeAlias = Union[
    StrictInt, StrictFloat, StrictBool, date, datetime, None, str, Any
]

SearchResultValuePrimitive: TypeAlias = Union[
    StrictInt, StrictFloat, StrictBool, date, datetime, None, str
]

SearchResultValue: TypeAlias = Union[
    SearchResultValuePrimitive, Mapping[str, SearchResultValuePrimitive], TypedDict
]

PassthroughSearchResultValue = TypeVar(
    "PassthroughSearchResultValue", bound=SearchResultValue
)


class TableRowValueObject(TypedDict):
    label: NotRequired[TableRowValuePrimitive]
    value: NotRequired[TableRowValuePrimitive]
    url: NotRequired[str]
    route: NotRequired[str]
    params: NotRequired[SerializableRecord]
    image: NotRequired[ImageDefinition]


class TableRowValueObjectModel(BaseModel):
    label: Optional[TableRowValuePrimitive] = None
    value: Optional[TableRowValuePrimitive] = None
    url: Optional[str] = None
    route: Optional[str] = None
    params: Optional[SerializableRecordModel] = None
    image: Optional[ImageDefinitionModel] = None


TableRowValue: TypeAlias = Union[TableRowValueObject, TableRowValuePrimitive]
TableRow: TypeAlias = Mapping[str, TableRowValue]


class TableMenuItem(TypedDict):
    label: str
    theme: NotRequired[Literal["danger"]]
    disabled: NotRequired[bool]
    route: NotRequired[str]
    params: NotRequired[SerializableRecord]
    url: NotRequired[str]


class TableMenuItemModel(BaseModel):
    label: str
    theme: Optional[Literal["danger"]]
    disabled: bool = False
    route: Optional[str] = None
    params: Optional[SerializableRecord] = None
    url: Optional[str] = None


class InternalTableRow(BaseModel):
    key: str
    data: TableRow
    menu: list[TableMenuItemModel] = Field(default_factory=list)
    filterValue: Optional[str] = None

    @override
    def revalidate(self) -> "InternalTableRowModel":
        return cast("InternalTableRowModel", super().revalidate())


class InternalTableRowModel(InternalTableRow):
    """
    Marker subclass of InternalTableRow that indicates the data is definitely validated.
    We do this model creation and validation in separate steps for performance and to avoid
    redefining the model structure.
    """


class SelectTableReturnModel(BaseModel):
    key: str


TR = TypeVar("TR", bound=TableRow)


class TableColumnDef(TypedDict, Generic[TR]):
    label: str
    renderCell: NotRequired[Callable[[TR], TableRowValue]]
    accessorKey: NotRequired[str]


class InternalTableColumn(BaseModel):
    label: str
    accessorKey: Optional[str] = None


class GridItemImage(TypedDict):
    url: NotRequired[Optional[str]]
    alt: NotRequired[str]
    fit: NotRequired[Literal["cover", "contain"]]
    aspectRatio: NotRequired[float]


class GridItemImageModel(BaseModel):
    url: Optional[str] = None
    alt: Optional[str] = None
    fit: Optional[Literal["cover", "contain"]] = None
    aspectRatio: Optional[float] = None


class GridItem(TypedDict):
    title: NotRequired[Optional[str]]
    description: NotRequired[Optional[str]]
    image: NotRequired[Optional[GridItemImage]]
    menu: NotRequired[list[TableMenuItem]]
    url: NotRequired[str]
    route: NotRequired[str]
    params: NotRequired[SerializableRecord]


class GridItemModel(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    image: Optional[GridItemImageModel] = None
    menu: Optional[list[TableMenuItemModel]] = None
    url: Optional[str] = None
    route: Optional[str] = None
    params: Optional[SerializableRecord] = None


class InternalGridItem(BaseModel):
    key: str
    data: GridItemModel
    filterValue: Optional[str] = None


PropsType = TypeVar("PropsType", bound=Type)
StateType = TypeVar("StateType", bound=Type)
ReturnType = TypeVar("ReturnType", bound=Type)


@dataclass
class MethodDef(Generic[PropsType, StateType, ReturnType]):
    props: PropsType
    state: StateType
    returns: ReturnType
    immediate: bool = False
    exclusive: bool = False
    supports_multiple: bool = False


class InputTextProps(BaseModel):
    help_text: Optional[str]
    placeholder: Optional[str]
    default_value: Optional[str]
    multiline: Optional[bool]
    lines: Optional[PositiveInt]
    disabled: Optional[bool]
    min_length: Optional[PositiveInt]
    max_length: Optional[PositiveInt]


class InputEmailProps(BaseModel):
    help_text: Optional[str]
    default_value: Optional[str]
    disabled: Optional[bool]
    placeholder: Optional[str]


CurrencyCode = Literal["USD", "CAD", "EUR", "GBP", "AUD", "CNY", "JPY"]


class InputNumberProps(BaseModel):
    min: Optional[Union[float, int]]
    max: Optional[Union[float, int]]
    prepend: Optional[str]
    help_text: Optional[str]
    placeholder: Optional[str]
    default_value: Optional[Union[float, int]]
    decimals: Optional[int]
    currency: Optional[CurrencyCode]
    disabled: Optional[bool]


class InputBooleanProps(BaseModel):
    help_text: Optional[str]
    default_value: Optional[str]
    disabled: Optional[bool]


class InputRichTextProps(BaseModel):
    help_text: Optional[str]
    disabled: Optional[bool]
    placeholder: Optional[str]
    default_value: Optional[str]


class InputUrlProps(BaseModel):
    help_text: Optional[str]
    default_value: Optional[str]
    allowed_protocols: Optional[list[str]]
    disabled: Optional[bool]
    placeholder: Optional[str]


class DateModel(BaseModel):
    year: int
    month: int
    day: int


class TimeModel(BaseModel):
    hour: int
    minute: int


class DateTimeModel(BaseModel):
    year: int
    month: int
    day: int
    hour: int
    minute: int


class InputDateProps(BaseModel):
    help_text: Optional[str]
    default_value: Optional[DateModel]
    disabled: Optional[bool]
    min: Optional[DateModel]
    max: Optional[DateModel]


class InputTimeProps(BaseModel):
    help_text: Optional[str]
    default_value: Optional[TimeModel]
    disabled: Optional[bool]
    min: Optional[TimeModel]
    max: Optional[TimeModel]


class InputDateTimeProps(BaseModel):
    help_text: Optional[str]
    default_value: Optional[DateTimeModel]
    disabled: Optional[bool]
    min: Optional[DateTimeModel]
    max: Optional[DateTimeModel]


class InputSpreadsheetProps(BaseModel):
    columns: dict[str, TypeValue]
    help_text: Optional[str]
    default_value: Optional[list[DeserializableRecordModel]]


class ConfirmProps(BaseModel):
    help_text: Optional[str]


class ConfirmIdentityProps(BaseModel):
    grace_period_ms: Optional[int]


class SelectTableProps(BaseModel):
    data: list[InternalTableRowModel]
    help_text: Optional[str]
    columns: list[InternalTableColumn]
    min_selections: Optional[PositiveInt]
    max_selections: Optional[PositiveInt]
    disabled: Optional[bool]
    default_page_size: Optional[PositiveInt] = None
    is_sortable: bool = True
    is_filterable: bool = True

    # private props
    total_records: PositiveInt
    selected_keys: Optional[list[str]] = None


class SelectTableState(BaseModel):
    query_term: Optional[str] = None
    sort_column: Optional[str] = None
    sort_direction: Optional[Literal["asc", "desc"]] = None
    offset: PositiveInt = 0
    page_size: PositiveInt
    is_select_all: bool = False


class SelectSingleProps(BaseModel):
    options: list[RichSelectOptionModel]
    help_text: Optional[str]
    default_value: Optional[RichSelectOptionModel]
    searchable: Optional[bool]
    disabled: Optional[bool]


class SelectSingleState(BaseModel):
    query_term: str


class SelectMultipleProps(BaseModel):
    options: list[LabelValueModel]
    help_text: Optional[str]
    default_value: list[LabelValueModel] = Field(default_factory=list)
    min_selections: Optional[PositiveInt]
    max_selections: Optional[PositiveInt]
    disabled: Optional[bool]


class DisplayHeadingProps(BaseModel):
    level: Optional[Literal[2, 3, 4]]
    description: Optional[str]
    menu_items: Optional[list[ButtonItemModel]]


class DisplayCodeProps(BaseModel):
    code: str
    language: Optional[str]


LinkTheme: TypeAlias = Literal["default", "danger"]


class DisplayLinkProps(BaseModel):
    route: Optional[str] = None
    url: Optional[str] = None
    params: Optional[SerializableRecord] = None
    theme: Optional[LinkTheme] = None


MetadataLayout: TypeAlias = Literal["card", "list", "grid"]


class DisplayMetadataProps(BaseModel):
    data: KeyValueObjectModel
    layout: MetadataLayout


class DisplayObjectProps(BaseModel):
    data: KeyValueObjectModel


class DisplayImageProps(BaseModel):
    url: Optional[str] = None
    alt: Optional[str] = None
    height: Optional[ImageSize] = None
    width: Optional[ImageSize] = None


class DisplayGridProps(BaseModel):
    help_text: Optional[str] = None
    data: list[InternalGridItem]
    ideal_column_width: Optional[PositiveInt] = None
    default_page_size: Optional[PositiveInt] = None
    is_filterable: bool = True
    # private props
    total_records: Optional[PositiveInt] = None
    is_async: bool


class DisplayGridState(BaseModel):
    query_term: Optional[str] = None
    offset: PositiveInt = 0
    page_size: PositiveInt


class DisplayTableProps(BaseModel):
    help_text: Optional[str] = None
    data: list[InternalTableRowModel]
    columns: list[InternalTableColumn]
    default_page_size: Optional[PositiveInt] = None
    is_sortable: bool = True
    is_filterable: bool = True
    # private props
    total_records: Optional[PositiveInt] = None
    is_async: bool


class DisplayTableState(BaseModel):
    query_term: Optional[str] = None
    sort_column: Optional[str] = None
    sort_direction: Optional[Literal["asc", "desc"]] = None
    offset: PositiveInt = 0
    page_size: PositiveInt


class DisplayVideoProps(BaseModel):
    url: Optional[str]
    height: Optional[ImageSize]
    width: Optional[ImageSize]
    loop: bool
    muted: bool


class DisplayProgressStepsSteps(BaseModel):
    completed: PositiveInt
    total: PositiveInt


class DisplayProgressStepsProps(BaseModel):
    steps: DisplayProgressStepsSteps
    current_step: Optional[PositiveInt]
    subtitle: Optional[str]


class DisplayProgressthroughListItem(BaseModel):
    label: str
    is_complete: bool
    result_description: Optional[str]


class DisplayProgressThroughListProps(BaseModel):
    items: list[DisplayProgressthroughListItem]


class SearchProps(BaseModel):
    help_text: Optional[str]
    results: list[InnerRenderableSearchResultModel]
    default_value: Optional[str]
    disabled: Optional[bool]
    placeholder: Optional[str]


class SearchState(BaseModel):
    query_term: str


# be sure to add any new methods to InputMethodName type above
input_schema: dict[InputMethodName, MethodDef] = {
    "INPUT_TEXT": MethodDef(
        props=InputTextProps,
        state=None,
        returns=str,
    ),
    "INPUT_EMAIL": MethodDef(
        props=InputEmailProps,
        state=None,
        returns=str,
    ),
    "INPUT_NUMBER": MethodDef(
        props=InputNumberProps,
        state=None,
        returns=float,
    ),
    "INPUT_BOOLEAN": MethodDef(
        props=InputBooleanProps,
        state=None,
        returns=bool,
    ),
    "INPUT_RICH_TEXT": MethodDef(
        props=InputRichTextProps,
        state=None,
        returns=str,
    ),
    "INPUT_URL": MethodDef(
        props=InputUrlProps,
        state=None,
        returns=str,
    ),
    "INPUT_DATE": MethodDef(
        props=InputDateProps,
        state=None,
        returns=DateModel,
    ),
    "INPUT_TIME": MethodDef(
        props=InputTimeProps,
        state=None,
        returns=TimeModel,
    ),
    "INPUT_DATETIME": MethodDef(
        props=InputDateTimeProps,
        state=None,
        returns=DateTimeModel,
    ),
    "INPUT_SPREADSHEET": MethodDef(
        props=InputSpreadsheetProps,
        state=None,
        returns=list[SerializableRecordModel],
    ),
    "CONFIRM": MethodDef(
        props=ConfirmProps,
        state=None,
        returns=bool,
        exclusive=True,
    ),
    "CONFIRM_IDENTITY": MethodDef(
        props=ConfirmIdentityProps,
        state=None,
        returns=bool,
        exclusive=True,
    ),
    "SELECT_TABLE": MethodDef(
        props=SelectTableProps,
        state=SelectTableState,
        returns=list[SelectTableReturnModel],
    ),
    "SELECT_SINGLE": MethodDef(
        props=SelectSingleProps,
        state=SelectSingleState,
        returns=RichSelectOptionModel,
    ),
    "SELECT_MULTIPLE": MethodDef(
        props=SelectMultipleProps,
        state=None,
        returns=list[LabelValueModel],
    ),
    "SEARCH": MethodDef(
        props=SearchProps,
        state=SearchState,
        returns=SearchResultValue,
        supports_multiple=True,
    ),
    "UPLOAD_FILE": MethodDef(
        props=UploadFileProps,
        state=UploadFileState,
        returns=InnerFileModel,
    ),
}

# be sure to add any new methods to DisplayMethodName type above
display_schema: dict[DisplayMethodName, MethodDef] = {
    "DISPLAY_CODE": MethodDef(
        props=DisplayCodeProps,
        state=None,
        returns=None,
    ),
    "DISPLAY_HEADING": MethodDef(
        props=DisplayHeadingProps,
        state=None,
        returns=None,
    ),
    "DISPLAY_LINK": MethodDef(
        props=DisplayLinkProps,
        state=None,
        returns=None,
    ),
    "DISPLAY_MARKDOWN": MethodDef(
        props={},
        state=None,
        returns=None,
    ),
    "DISPLAY_METADATA": MethodDef(
        props=DisplayMetadataProps,
        state=None,
        returns=None,
    ),
    "DISPLAY_IMAGE": MethodDef(
        props=DisplayImageProps,
        state=None,
        returns=None,
    ),
    "DISPLAY_OBJECT": MethodDef(
        props=DisplayObjectProps,
        state=None,
        returns=None,
    ),
    "DISPLAY_GRID": MethodDef(
        props=DisplayGridProps,
        state=DisplayGridState,
        returns=None,
    ),
    "DISPLAY_TABLE": MethodDef(
        props=DisplayTableProps,
        state=DisplayTableState,
        returns=None,
    ),
    "DISPLAY_VIDEO": MethodDef(
        props=DisplayVideoProps,
        state=None,
        returns=None,
    ),
    "DISPLAY_PROGRESS_STEPS": MethodDef(
        props=DisplayProgressStepsProps,
        state=None,
        returns=None,
        immediate=True,
    ),
    "DISPLAY_PROGRESS_INDETERMINATE": MethodDef(
        props={},
        state=None,
        returns=None,
        immediate=True,
    ),
    "DISPLAY_PROGRESS_THROUGH_LIST": MethodDef(
        props=DisplayProgressThroughListProps,
        state=None,
        returns=None,
    ),
}

io_schema: dict[MethodName, MethodDef] = cast(
    dict[MethodName, MethodDef],
    {
        **input_schema,
        **display_schema,
    },
)


class IOSchema(Generic[MN]):
    method_def: MethodDef

    def __init__(self, method_name: MN):
        self.method_def = io_schema[method_name]

    @classmethod
    def props(cls):
        return cls.method_def.props


def resolves_immediately(method_name: MethodName) -> bool:
    return io_schema[method_name].immediate


def dump_io_render(io_render: dict[str, Any]) -> dict[str, Any]:
    obj = {}
    for key, val in io_render.items():
        if key == "to_render":
            obj[snake_to_camel(key)] = [
                dict_keys_to_camel(dict_strip_none(info)) for info in val
            ]
        elif key == "validation_error_message" and val is None:
            pass
        elif key == "continue_button":
            if val is None:
                continue
            obj[snake_to_camel(key)] = dict_keys_to_camel(dict_strip_none(val))
        else:
            obj[snake_to_camel(key)] = val

    return obj


def json_dumps_io_render(io_render: dict[str, Any], *args, **kwargs) -> str:
    # we don't want to clobber any user-provided keys in props
    return json.dumps(dump_io_render(io_render), *args, **kwargs)


class IORender(BaseModel):
    id: UUID
    input_group_key: UUID
    to_render: list[ComponentRenderInfo]
    kind: Literal["RENDER"] = "RENDER"
    validation_error_message: Optional[str] = None
    continue_button: Optional[ButtonConfig] = None

    class Config:
        json_dumps = json_dumps_io_render


class IOResponse(PydanticBaseModel):
    id: UUID
    input_group_key: Optional[str] = None
    transaction_id: str
    kind: Literal["RETURN", "SET_STATE", "CANCELED"]
    values: list[Any]

    class Config:
        json_loads = json_loads_some_snake("transaction_id", "input_group_key")
        json_dumps = json_dumps_some_snake("transaction_id", "input_group_key")


def dump_method(method_name: MethodName) -> str:
    method_def = io_schema[method_name]
    props = method_def.props
    pieces = method_name.split("_", maxsplit=1)
    if len(pieces) > 1:
        [namespace, fn_name] = pieces
    else:
        namespace = "IO"
        [fn_name] = pieces

    contents = io.StringIO()

    print(f"{namespace}:", file=contents)
    print(f"def {fn_name.lower()}(", file=contents)
    print("    self,", file=contents)
    print("    label: str,", file=contents)

    prop_names = []
    if not isinstance(props, dict):
        for name, field in props.__fields__.items():
            prop_names.append(name)
            field = cast(ModelField, field)
            if str(field.outer_type_).startswith("<class"):
                field_type: str = field.outer_type_.__name__
            else:
                field_type: str = str(field.outer_type_)
            if not field.required:
                field_type = f"Optional[{field_type}]"
                field_type += f" = {field.default}"

            print(f"    {name}: {field_type},", file=contents)

    return_type = "None"
    if method_def.returns is not None:
        return_type = method_def.returns.__name__
    print(f') -> IOPromise[Literal["{method_name}"], {return_type}]:', file=contents)
    print(
        f"""\
        c = Component(
            method_name="{method_name}",
            label=label,\
        """,
        file=contents,
    )

    if isinstance(props, dict):
        print("            initial_props={},", file=contents)
    else:
        props_type = cast(Type[PydanticBaseModel], props)
        props_model_name = props_type.__name__

        print(f"            initial_props={props_model_name}(", file=contents)

        for name in prop_names:
            print(f"                {name}={name},", file=contents)

        print("            ).dict(),", file=contents)

    print(
        """\
        )
        return IOPromise(c, renderer=self._renderer)
        """,
        file=contents,
    )

    output = contents.getvalue()
    contents.close()
    return output


def dump_all_methods():
    for method_name in io_schema.keys():
        try:
            print(dump_method(method_name))
        except Exception as err:
            print(f"Failed to dump method for {method_name}:", err, file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
