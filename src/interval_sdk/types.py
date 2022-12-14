from typing import Optional, Union, TYPE_CHECKING
from typing_extensions import override
from pydantic import BaseModel as PydanticBaseModel
from pydantic.generics import GenericModel as PydanticGenericModel

if TYPE_CHECKING:
    from pydantic.typing import AbstractSetIntStr, MappingIntStrAny

from .util import *


class BaseModel(PydanticBaseModel):
    class Config:
        json_loads = json_loads_camel
        json_dumps = json_dumps_snake

    @override
    def dict(
        self,
        include: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        exclude: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        by_alias: bool = False,
        skip_defaults: Optional[bool] = None,
        exclude_unset: bool = True,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ):
        return super().dict(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            skip_defaults=skip_defaults,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )


class GenericModel(PydanticGenericModel):
    class Config:
        json_loads = json_loads_camel
        json_dumps = json_dumps_snake
