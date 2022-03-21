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
)
from datetime import date, datetime
from uuid import UUID
import io, json, sys

from pydantic import BaseModel as PydanticBaseModel
from pydantic.fields import ModelField


from .types import (
    BaseModel,
    GenericModel,
    snake_to_camel,
    dict_keys_to_camel,
    json_dumps_some_snake,
    json_loads_some_snake,
)

# TODO: Try generating most of this with datamode-code-generator
# https://github.com/koxudaxi/datamodel-code-generator/

MethodName = Literal[
    "INPUT_TEXT",
    "INPUT_EMAIL",
    "INPUT_NUMBER",
    "INPUT_BOOLEAN",
    "INPUT_RICH_TEXT",
    "INPUT_SPREADSHEET",
    "CONFIRM",
    "SELECT_TABLE",
    "SELECT_SINGLE",
    "SELECT_MULTIPLE",
    # Intentionally not implementing
    # "SELECT_USER",
    "DISPLAY_HEADING",
    "DISPLAY_MARKDOWN",
    "DISPLAY_OBJECT",
    "DISPLAY_TABLE",
    "DISPLAY_PROGRESS_STEPS",
    "DISPLAY_PROGRESS_INDETERMINATE",
    "DISPLAY_PROGRESS_THROUGH_LIST",
]

MN = TypeVar("MN", bound=MethodName)


class ComponentRenderInfo(GenericModel, Generic[MN]):
    method_name: MN
    label: str
    props: Any
    is_stateful: bool
    is_optional: bool

    class Config:
        json_loads = json_loads_some_snake("method_name", "is_stateful", "is_optional")
        json_dumps = json_dumps_some_snake("method_name", "is_stateful", "is_optional")


TypeValue = Literal[
    "string",
    "string?",
    "number",
    "number?",
    "boolean",
    "boolean?",
]

# TODO: Passthrough?
class LabelValue(BaseModel):
    label: str
    value: str


class RichSelectOption(BaseModel):
    label: str
    value: str
    description: str
    image_url: str


ObjectLiteral: TypeAlias = bool | int | float | date | datetime | None | str

KeyValueObject: TypeAlias = (
    ObjectLiteral | list["KeyValueObject"] | dict[str, "KeyValueObject"]
)


class KeyValueObjectModel(BaseModel):
    __root__: ObjectLiteral | list[KeyValueObjectModel | None] | dict[
        str, KeyValueObjectModel | None
    ]


KeyValueObjectModel.update_forward_refs()

Deserializable: TypeAlias = str | int | float | bool | None
DeserializableRecord: TypeAlias = Mapping[str, Deserializable]
Serializable: TypeAlias = str | int | float | bool | None | date | datetime
SerializableRecord: TypeAlias = Mapping[str, Serializable]


class TableRowLabelValue(BaseModel):
    _label: str
    _value: ObjectLiteral


RawActionReturnData: TypeAlias = Mapping[str, SerializableRecord]
IOFunctionReturnType: TypeAlias = SerializableRecord | None


class ParsedActionReturnDataLink(BaseModel):
    data_kind: Literal["link"] | None
    value: str


ParsedActionReturnDataValue = SerializableRecord | ParsedActionReturnDataLink

ParsedActionReturnData: TypeAlias = dict[str, ParsedActionReturnDataValue]


class ActionResult(BaseModel):
    schema_version: Literal[0, 1] = 1
    status: Literal["SUCCESS", "FAILURE"]
    data: IOFunctionReturnType | None


TableRowValue = str | int | float | bool | None | date | datetime | TableRowLabelValue

TableRow: TypeAlias = dict[str, TableRowValue]


class TableColumnDef(BaseModel):
    key: str
    label: Optional[str]
    formatter: Optional[Callable[[Any], str]]


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


class InputEmailProps(BaseModel):
    help_text: Optional[str]
    default_value: Optional[str]


class InputNumberProps(BaseModel):
    min: Optional[int]
    max: Optional[int]
    prepend: Optional[str]
    help_text: Optional[str]
    default_value: Optional[str]


class InputBooleanProps(BaseModel):
    help_text: Optional[str]
    default_value: Optional[str]


class InputRichTextProps(BaseModel):
    help_text: Optional[str]


class InputSpreadsheetProps(BaseModel):
    columns: dict[str, TypeValue]
    help_text: Optional[str]


class ConfirmProps(BaseModel):
    help_text: Optional[str]


class SelectTableProps(BaseModel):
    data: list[TableRow]
    help_text: Optional[str]
    columns: Optional[TableColumnDef]


class SelectSingleProps(BaseModel):
    options: list[RichSelectOption]
    help_text: Optional[str]
    default_value: Optional[RichSelectOption]
    searchable: Optional[bool]


class SelectSingleState(BaseModel):
    query_term: str


class SelectMultipleProps(BaseModel):
    options: list[LabelValue]
    help_text: Optional[str]
    default_value: list[LabelValue] = []


class DisplayObjectProps(BaseModel):
    data: KeyValueObjectModel


class DisplayTableProps(BaseModel):
    data: list[TableRow]
    help_text: Optional[str]
    columns: Optional[list[TableColumnDef]]


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


io_schema: dict[MethodName, MethodDef] = {
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
        returns=int,
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
    "SELECT_TABLE": MethodDef(
        props=SelectTableProps,
        state=None,
        returns=list[TableRow],
    ),
    "SELECT_SINGLE": MethodDef(
        props=SelectSingleProps,
        state=SelectSingleState,
        returns=RichSelectOption,
    ),
    "SELECT_MULTIPLE": MethodDef(
        props=SelectMultipleProps,
        state=None,
        returns=list[LabelValue],
    ),
    "DISPLAY_HEADING": MethodDef(
        props={},
        state=None,
        returns=None,
    ),
    "DISPLAY_MARKDOWN": MethodDef(
        props={},
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


class IOSchema(Generic[MN]):
    method_def: MethodDef

    def __init__(self, method_name: MN):
        self.method_def = io_schema[method_name]

    @classmethod
    def props(cls):
        return cls.method_def.props


def resolves_immediately(method_name: MethodName) -> bool:
    return io_schema[method_name].immediate


def json_dumps_io_render(io_render: dict[str, Any], *args, **kwargs) -> str:
    """
    We don't want to clobber any user-provided keys in props.
    """
    obj = {}
    for key, val in io_render.items():
        if key == "to_render":
            obj[snake_to_camel(key)] = [dict_keys_to_camel(info) for info in val]
        else:
            obj[snake_to_camel(key)] = val

    print(obj)
    return json.dumps(obj, *args, **kwargs)


class IORender(BaseModel):
    id: UUID
    input_group_key: UUID
    to_render: list[ComponentRenderInfo]
    kind: Literal["RENDER"]

    class Config:
        json_dumps = json_dumps_io_render


class IOResponse(PydanticBaseModel):
    id: UUID
    transaction_id: str
    kind: Literal["RETURN", "SET_STATE"]
    values: list[Any]

    class Config:
        json_loads = json_loads_some_snake("transaction_id")
        json_dumps = json_dumps_some_snake("transaction_id")


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
        f"""\
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
