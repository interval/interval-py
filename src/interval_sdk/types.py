from typing import Any, Callable, Optional, TypeVar, Union, TYPE_CHECKING

from typing_extensions import override
from pydantic import BaseModel as PydanticBaseModel, validate_model
from pydantic.generics import GenericModel as PydanticGenericModel

from .util import snake_to_camel

if TYPE_CHECKING:
    from pydantic.typing import AbstractSetIntStr, MappingIntStrAny


class NotInitializedError(Exception):
    pass


class IntervalError(Exception):
    pass


BaseModelSelf = TypeVar("BaseModelSelf", bound="BaseModel")


def alias_generator(field: str) -> str:
    if field.startswith("_"):
        return field
    return snake_to_camel(field)


class BaseModel(PydanticBaseModel):
    class Config:
        alias_generator = alias_generator
        allow_population_by_field_name = True

    @override
    def dict(
        self,
        include: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        exclude: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        by_alias: bool = True,
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

    @override
    def json(
        self,
        include: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        exclude: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        by_alias: bool = True,
        skip_defaults: Optional[bool] = None,
        exclude_unset: bool = True,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        encoder: Optional[Callable[[Any], Any]] = None,
        models_as_dict: bool = True,
    ):
        return super().json(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            skip_defaults=skip_defaults,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            encoder=encoder,
            models_as_dict=models_as_dict,
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
        alias_generator = alias_generator
        allow_population_by_field_name = True

    @override
    def dict(
        self,
        include: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        exclude: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        by_alias: bool = True,
        skip_defaults: Optional[bool] = None,
        exclude_unset: bool = False,
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

    @override
    def json(
        self,
        include: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        exclude: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        by_alias: bool = True,
        skip_defaults: Optional[bool] = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        encoder: Optional[Callable[[Any], Any]] = None,
        models_as_dict: bool = True,
    ):
        return super().json(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            skip_defaults=skip_defaults,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            encoder=encoder,
            models_as_dict=models_as_dict,
        )
