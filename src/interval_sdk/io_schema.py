from __future__ import annotations
from dataclasses import dataclass
import traceback
from typing import (
    cast,
    Any,
    Callable,
    Optional,
    Literal,
    TypeAlias,
    Generic,
    TypeVar,
    Mapping,
    Type,
    TypedDict,
)
from datetime import date, time, datetime
from uuid import UUID
import io, json, sys
from typing_extensions import NotRequired
from pydantic import (
    BaseModel as PydanticBaseModel,
    Field,
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

DisplayMethodName = Literal[
    "DISPLAY_CODE",
    "DISPLAY_HEADING",
    "DISPLAY_IMAGE",
    "DISPLAY_LINK",
    "DISPLAY_MARKDOWN",
    "DISPLAY_METADATA",
    "DISPLAY_OBJECT",
    "DISPLAY_TABLE",
    "DISPLAY_VIDEO",
    "DISPLAY_PROGRESS_STEPS",
    "DISPLAY_PROGRESS_INDETERMINATE",
    "DISPLAY_PROGRESS_THROUGH_LIST",
]

MethodName = InputMethodName | DisplayMethodName

MN = TypeVar("MN", bound=MethodName)


class ComponentRenderInfo(GenericModel, Generic[MN]):
    method_name: MN
    label: str
    props: Any
    is_stateful: bool
    is_optional: bool
    validation_error_message: str | None = None

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


class ButtonConfig(BaseModel):
    label: str | None = None
    theme: Literal["primary", "secondary", "danger"] | None = None


class RichSelectOption(TypedDict):
    label: ObjectLiteral
    value: ObjectLiteral
    description: NotRequired[str]
    imageUrl: NotRequired[str]


PassthroughRichSelectOption = TypeVar(
    "PassthroughRichSelectOption", bound=RichSelectOption | str
)


class RichSelectOptionModel(BaseModel):
    label: ObjectLiteral
    value: ObjectLiteral
    description: str | None = None
    imageUrl: str | None = None


class KeyValueObjectModel(BaseModel):
    __root__: ObjectLiteral | list[KeyValueObjectModel | None] | dict[
        str, KeyValueObjectModel | None
    ]


class ImageSchema(TypedDict):
    url: NotRequired[str]
    alt: NotRequired[str]
    size: NotRequired[ImageSize]


class ImageModel(BaseModel):
    url: Optional[str] = None
    alt: Optional[str] = None
    size: Optional[ImageSize] = None


ButtonTheme = Literal["danger"]


class ButtonItem(TypedDict):
    label: str
    theme: Optional[ButtonTheme]
    params: Optional[SerializableRecord]
    url: Optional[str]
    disabled: Optional[bool]


class ButtonItemModel(BaseModel):
    label: str
    theme: ButtonTheme | None = None
    route: str | None = None
    params: SerializableRecord | None = None
    url: str | None = None
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
    "PassthroughRenderableSearchResult", bound=RenderableSearchResult
)


class InnerRenderableSearchResultModel(RenderableSearchResultModel):
    value: str


class FileUploadProps(BaseModel):
    allowed_extensions: Optional[list[str]]
    help_text: Optional[str]
    upload_url: Optional[str]
    download_url: Optional[str]
    disabled: Optional[bool]


class FileUploadState(BaseModel):
    name: str
    type: str


class InnerFileModel(BaseModel):
    last_modified: datetime | None = None
    name: str
    type: str
    size: int
    url: str


KeyValueObjectModel.update_forward_refs()


class LabelValue(TypedDict):
    label: ObjectLiteral
    value: ObjectLiteral


PassthroughLabelValue = TypeVar("PassthroughLabelValue", bound=LabelValue | str)


class LabelValueModel(BaseModel):
    label: ObjectLiteral
    value: ObjectLiteral


RawActionReturnData: TypeAlias = Mapping[str, Serializable]
IOFunctionReturnType: TypeAlias = Serializable | SerializableRecord | None


class ParsedActionReturnDataLink(BaseModel):
    data_kind: Literal["link"] | None
    value: str


ParsedActionReturnDataValue = SerializableRecord | ParsedActionReturnDataLink

ParsedActionReturnData: TypeAlias = dict[str, ParsedActionReturnDataValue]


class DeserializableModel(BaseModel):
    __root__: StrictInt | StrictFloat | StrictBool | None | str


class DeserializableRecordModel(BaseModel):
    __root__: dict[str, DeserializableModel | None]


class SerializableModel(BaseModel):
    __root__: StrictInt | StrictFloat | StrictBool | None | date | time | datetime | str


class SerializableRecordModel(BaseModel):
    __root__: dict[str, SerializableModel | None]


class IOFunctionReturnModel(BaseModel):
    __root__: DeserializableModel | DeserializableRecordModel | None


class ActionResult(BaseModel):
    schema_version: Literal[0, 1] = 1
    status: Literal["SUCCESS", "FAILURE"]
    data: IOFunctionReturnModel


TableRowValuePrimitive = (
    StrictInt | StrictFloat | StrictBool | date | datetime | None | str | Any
)

SearchResultValuePrimitive = StrictInt | StrictFloat | StrictBool | str

SearchResultValue = SearchResultValuePrimitive | dict[str, SearchResultValuePrimitive]

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
    label: TableRowValuePrimitive | None = None
    value: TableRowValuePrimitive | None = None
    url: str | None = None
    route: str | None = None
    params: SerializableRecordModel | None = None
    image: ImageDefinitionModel | None = None


TableRowValue: TypeAlias = TableRowValueObject | TableRowValuePrimitive
TableRow: TypeAlias = Mapping[str, TableRowValue]


class TableRowValueModel(BaseModel):
    __root__: TableRowValuePrimitive | TableRowValueObjectModel


TableRowModel: TypeAlias = dict[str, TableRowValueModel | None]


class TableMenuItem(TypedDict):
    label: str
    theme: NotRequired[Literal["danger"]]
    disabled: NotRequired[bool]
    route: NotRequired[str]
    params: NotRequired[SerializableRecord]
    url: NotRequired[str]


class TableMenuItemModel(BaseModel):
    label: str
    theme: Literal["danger"] | None
    disabled: bool = False
    route: str | None = None
    params: SerializableRecord | None = None
    url: str | None = None


class InternalTableRow(BaseModel):
    key: str
    data: TableRowModel
    menu: list[TableMenuItemModel] = Field(default_factory=list)
    filterValue: str | None = None


class SelectTableReturnModel(BaseModel):
    key: str


class TableColumnDef(TypedDict):
    label: str
    renderCell: NotRequired[Callable[[Any], TableRowValue]]
    accessorKey: NotRequired[str]


class InternalTableColumn(BaseModel):
    label: str
    accessorKey: Optional[str] = None


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


class InputTextProps(BaseModel):
    help_text: Optional[str]
    default_value: Optional[str]
    multiline: Optional[bool]
    lines: Optional[int]
    disabled: Optional[bool]
    placeholder: Optional[str]


class InputEmailProps(BaseModel):
    help_text: Optional[str]
    default_value: Optional[str]
    disabled: Optional[bool]
    placeholder: Optional[str]


class InputNumberProps(BaseModel):
    min: Optional[float | int]
    max: Optional[float | int]
    default_value: Optional[float | int]
    decimals: Optional[int]
    prepend: Optional[str]
    help_text: Optional[str]
    disabled: Optional[bool]
    placeholder: Optional[str]


class InputBooleanProps(BaseModel):
    help_text: Optional[str]
    default_value: Optional[str]
    disabled: Optional[bool]


class InputRichTextProps(BaseModel):
    help_text: Optional[str]
    disabled: Optional[bool]
    placeholder: Optional[str]


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


class InputTimeProps(BaseModel):
    help_text: Optional[str]
    default_value: Optional[TimeModel]
    disabled: Optional[bool]


class InputDateTimeProps(BaseModel):
    help_text: Optional[str]
    default_value: Optional[DateTimeModel]
    disabled: Optional[bool]


class InputSpreadsheetProps(BaseModel):
    columns: dict[str, TypeValue]
    help_text: Optional[str]


class ConfirmProps(BaseModel):
    help_text: Optional[str]


class ConfirmIdentityProps(BaseModel):
    grace_period_ms: Optional[int]


class SelectTableProps(BaseModel):
    data: list[InternalTableRow]
    help_text: Optional[str]
    columns: list[InternalTableColumn]
    min_selections: Optional[int]
    max_selections: Optional[int]
    total_records: int
    selected_keys: list[str] | None = None
    disabled: Optional[bool]
    default_page_size: int | None = None
    is_sortable: bool = True
    is_filterable: bool = True


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
    default_value: list[LabelValueModel] = []
    min_selections: Optional[int]
    max_selections: Optional[int]
    disabled: Optional[bool]


class DisplayCodeProps(BaseModel):
    code: str
    language: Optional[str]


LinkTheme: TypeAlias = Literal["default", "danger"]


class DisplayLinkProps(BaseModel):
    action: str | None
    url: str | None
    params: dict[str, Any] | None
    theme: LinkTheme | None


MetadataLayout: TypeAlias = Literal["card", "list", "grid"]


class DisplayMetadataProps(BaseModel):
    data: KeyValueObjectModel
    layout: MetadataLayout


class DisplayObjectProps(BaseModel):
    data: KeyValueObjectModel


ImageSize: TypeAlias = Literal["thumbnail", "small", "medium", "large"]


class ImageDefinition(TypedDict):
    url: str
    alt: Optional[str]
    size: Optional[ImageSize]


class ImageDefinitionModel(BaseModel):
    url: str
    alt: str | None = None
    size: ImageSize | None = None


class DisplayImageProps(BaseModel):
    url: Optional[str]
    alt: Optional[str]
    height: Optional[ImageSize]
    width: Optional[ImageSize]


class DisplayTableProps(BaseModel):
    help_text: Optional[str] = None
    data: list[InternalTableRow]
    columns: list[InternalTableColumn]
    default_page_size: int | None = None
    is_sortable: bool = True
    is_filterable: bool = True
    # private props
    total_records: int | None = None
    is_async: bool


class DisplayTableState(BaseModel):
    query_term: Optional[str] = None
    sort_column: Optional[str] = None
    sort_direction: Optional[Literal["asc", "desc"]] = None
    offset: int = 0
    page_size: int


class SelectTableState(BaseModel):
    query_term: Optional[str] = None
    sort_column: Optional[str] = None
    sort_direction: Optional[Literal["asc", "desc"]] = None
    offset: int = 0
    page_size: int
    is_select_all: bool = False


class DisplayVideoProps(BaseModel):
    url: Optional[str]
    alt: Optional[str]
    height: Optional[ImageSize]
    width: Optional[ImageSize]
    loop: bool
    muted: bool


class DisplayProgressStepsSteps(BaseModel):
    completed: int
    total: int


class DisplayProgressStepsProps(BaseModel):
    steps: DisplayProgressStepsSteps
    current_step: Optional[int]
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
    disabled: Optional[bool]
    placeholder: Optional[str]


class SearchState(BaseModel):
    query_term: str


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
        returns=list[SerializableRecord],
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
    ),
    "UPLOAD_FILE": MethodDef(
        props=FileUploadProps,
        state=FileUploadState,
        returns=InnerFileModel,
    ),
}

display_schema: dict[DisplayMethodName, MethodDef] = {
    "DISPLAY_CODE": MethodDef(
        props=DisplayCodeProps,
        state=None,
        returns=None,
    ),
    "DISPLAY_HEADING": MethodDef(
        props={},
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
    """
    We don't want to clobber any user-provided keys in props.
    """
    return json.dumps(dump_io_render(io_render), *args, **kwargs)


class IORender(BaseModel):
    id: UUID
    input_group_key: UUID
    to_render: list[ComponentRenderInfo]
    kind: Literal["RENDER"] = "RENDER"
    validation_error_message: str | None = None
    continue_button: ButtonConfig | None = None

    class Config:
        json_dumps = json_dumps_io_render


class IOResponse(PydanticBaseModel):
    id: UUID
    input_group_key: str | None = None
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
                field_type += " | None"
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
            traceback.print_exception(err, file=sys.stderr)
