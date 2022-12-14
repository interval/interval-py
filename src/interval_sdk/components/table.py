from datetime import date, datetime, time
from typing import Callable, Iterable, cast, Any

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


def drop_render(col: TableColumnDef) -> InternalTableColumn:
    d = dict(col)
    if "renderCell" in d:
        del d["renderCell"]

    return cast(InternalTableColumn, d)
