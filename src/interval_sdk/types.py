from pydantic import BaseModel as PydanticBaseModel
from pydantic.generics import GenericModel as PydanticGenericModel

from .util import *


class BaseModel(PydanticBaseModel):
    class Config:
        json_loads = json_loads_camel
        json_dumps = json_dumps_snake


class GenericModel(PydanticGenericModel):
    class Config:
        json_loads = json_loads_camel
        json_dumps = json_dumps_snake
