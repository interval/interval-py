from typing import Any, Optional, TypeVar, Union, TYPE_CHECKING

from typing_extensions import override
from pydantic import BaseModel as PydanticBaseModel, validate_model
from pydantic.generics import GenericModel as PydanticGenericModel

from .util import json_loads_camel, json_dumps_snake

if TYPE_CHECKING:
    from pydantic.typing import AbstractSetIntStr, MappingIntStrAny


class NotInitializedError(Exception):
    pass


class IntervalError(Exception):
    pass


BaseModelSelf = TypeVar("BaseModelSelf", bound="BaseModel")


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

    def revalidate(self: BaseModelSelf) -> BaseModelSelf:
        """
        Revalidates an existing model, for actually validating models which were
        created with .construct() for performance.
        Based on PydanticBaseModel.from_orm().
        """
        obj: Any = self._decompose_class(self)
        _values, _fields_set, validation_error = validate_model(self.__class__, obj)
        if validation_error:
            raise validation_error
        return self


class GenericModel(PydanticGenericModel):
    class Config:
        json_loads = json_loads_camel
        json_dumps = json_dumps_snake
