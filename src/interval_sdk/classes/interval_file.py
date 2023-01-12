from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
import urllib.request, json, os.path

from ..types import IntervalError


@dataclass
class IntervalFile:
    last_modified: Optional[datetime]
    name: str
    type: str
    size: int
    url: str

    @property
    def extension(self) -> str:
        _, extension = os.path.splitext(self.name)
        return extension

    def text(self) -> str:
        if not self.url:
            raise IntervalError("Cannot get text from a public file")
        response = urllib.request.urlopen(self.url)
        buffer = response.read()
        return buffer.decode("utf-8")

    def json(self) -> Any:
        response = urllib.request.urlopen(self.url)
        buffer = response.read()
        return json.loads(buffer.decode("utf-8"))

    def read(self):
        response = urllib.request.urlopen(self.url)
        return response.read()
