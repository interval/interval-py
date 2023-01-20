from dataclasses import dataclass
from datetime import date, datetime, time
from typing import (
    Awaitable,
    Callable,
    Generic,
    Iterable,
    Optional,
    TypeVar,
    Union,
)
from typing_extensions import TypeAlias

from ..io_schema import (
    GridItem,
    GridItemModel,
    InternalGridItem,
)
from ..util import (
    format_datelike,
)

TABLE_DATA_BUFFER_SIZE = 500


@dataclass
class GridDataFetcherState:
    query_term: Optional[str]
    offset: int
    page_size: int


GI = TypeVar("GI")


@dataclass
class FetchedGridData(Generic[GI]):
    data: list[GI]
    total_records: Optional[int] = None


GridDataFetcher: TypeAlias = Callable[
    [GridDataFetcherState],
    Awaitable[Union[FetchedGridData, list[GI], tuple[list[GI], int]]],
]


def serialize_grid_item(
    key: str,
    item: GI,
    render_item: Callable[[GI], GridItem],
) -> InternalGridItem:
    filter_values: list[str] = []

    if item is not None:
        if isinstance(item, dict):
            filter_values = [
                format_datelike(v) if isinstance(v, (date, time, datetime)) else v
                for v in item.values()
            ]

    # skip validation here, it will be performed again when being sent
    return InternalGridItem.construct(
        key=key,
        data=GridItemModel.parse_obj(render_item(item)),
        filterValue=" ".join(filter_values).lower(),
    )


def filter_items(
    data: Iterable[InternalGridItem],
    query_term: Optional[str] = None,
) -> list[InternalGridItem]:
    if query_term is None:
        return list(data)

    return [
        row
        for row in data
        if row.filterValue is None or query_term.lower() in row.filterValue
    ]
