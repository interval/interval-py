from datetime import date, datetime, time
from typing import Callable, Iterable, Literal, TypeAlias, cast, Any
import math

from ..io_schema import (
    InternalTableColumn,
    TableRow,
    TableColumnDef,
    InternalTableRow,
    TableRowValueObject,
)
from ..util import (
    format_date,
    format_datetime,
    format_time,
    serialize_dates,
    SerializableRecord,
)

TABLE_DATA_BUFFER_SIZE = 500


def serialize_table_row(
    key: str,
    row: TableRow | Any,
    columns: Iterable[TableColumnDef],
) -> InternalTableRow:
    row = cast(TableRow, serialize_dates(cast(SerializableRecord, row)))
    rendered_row: TableRow = {}
    filter_values: list[str] = []

    for i, col in enumerate(columns):
        accessor_key = col["accessorKey"] if "accessorKey" in col else str(i)
        val = (
            col["renderCell"](row)
            if "renderCell" in col
            else row[col["accessorKey"]]
            if ("accessorKey" in col and col["accessorKey"] in row)
            else None
        )

        # TODO: image

        if val is not None:
            if val is dict:
                val = cast(TableRowValueObject, val)
                if "label" in val and val["label"] is not None:
                    if isinstance(val["label"], datetime):
                        filter_values.append(format_datetime(val["label"]))
                    elif isinstance(val["label"], time):
                        filter_values.append(format_time(val["label"]))
                    elif isinstance(val["label"], date):
                        filter_values.append(format_date(val["label"]))
                    else:
                        filter_values.append(str(val["label"]))
            elif isinstance(val, datetime):
                filter_values.append(format_datetime(val))
            elif isinstance(val, date):
                filter_values.append(format_date(val))
            elif isinstance(val, time):
                filter_values.append(format_time(val))
            else:
                filter_values.append(str(val))

        rendered_row[accessor_key] = val

    return {
        "key": key,
        "data": rendered_row,
        "filterValue": " ".join(filter_values).lower(),
        # TODO: menu
    }


def columns_builder(
    data: Iterable[TableRow | Any] | None = None,
    columns: Iterable[TableColumnDef | str] | None = None,
    log_missing_column: Callable[[str], None] | None = None,
) -> list[TableColumnDef]:
    # using a dict instead of a set because dicts are ordered and sets aren't
    data_columns: dict[str, None] = (
        {col: None for row in data for col in row.keys()} if data is not None else {}
    )

    if columns:

        def normalize_col(col: TableColumnDef | str) -> TableColumnDef:
            if col is str:
                col = cast(str, col)

                if log_missing_column is not None and col not in data_columns:
                    log_missing_column(col)

                return {
                    "label": col,
                    "accessorKey": col,
                }

            col = cast(TableColumnDef, col)

            if (
                log_missing_column is not None
                and "accessorKey" in col
                and col["accessorKey"] not in data_columns
            ):
                log_missing_column(col["accessorKey"])

            return col

        return list(map(normalize_col, columns))

    return [{"label": label, "accessorKey": label} for label in data_columns]


def filter_rows(
    data: Iterable[InternalTableRow],
    query_term: str | None = None,
) -> list[InternalTableRow]:
    if query_term is None:
        return list(data)

    return [
        row
        for row in data
        if "filterValue" not in row or query_term.lower() in row["filterValue"]
    ]


SortableValue: TypeAlias = str | int | float | date | time | datetime


def get_sortable_value(row: InternalTableRow, sort_by_column: str) -> SortableValue:
    sort_val = None

    if row is not None and "data" in row:
        if sort_by_column in row["data"]:
            sort_val = row["data"][sort_by_column]

    if sort_val is not None and isinstance(sort_val, dict):
        if "value" in sort_val and sort_val["value"] is not None:
            return cast(SortableValue, sort_val["value"])
        if "label" in sort_val and sort_val["label"] is not None:
            return cast(SortableValue, sort_val["label"])
    elif sort_val is not None:
        return cast(SortableValue, sort_val)

    return -math.inf


def sort_rows(
    data: Iterable[InternalTableRow],
    column: str | None,
    direction: Literal["asc", "desc"] | None,
) -> list[InternalTableRow]:
    if column is None or direction is None:
        return sorted(data, key=lambda row: int(row["key"]))

    return sorted(
        data,
        key=lambda row: get_sortable_value(row, column),
        reverse=direction == "desc",
    )


def drop_render(col: TableColumnDef) -> InternalTableColumn:
    d = dict(col)
    if "renderCell" in d:
        del d["renderCell"]

    return cast(InternalTableColumn, d)
