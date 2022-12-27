from dataclasses import dataclass
from datetime import datetime
import urllib.request, json


@dataclass
class IntervalFile:
    extension: str
    name: str
    type: str
    size: int
    private_url: str
    last_modified: datetime | None = None

    class Config:
        allow_population_by_field_name = True

    async def url(self):
        return self.private_url

    async def text(self):
        if not self.private_url:
            raise ValueError("Cannot get text from a public file")
        response = urllib.request.urlopen(self.private_url)
        buffer = response.read()
        return buffer.decode("utf-8")

    async def json(self):
        response = urllib.request.urlopen(self.private_url)
        buffer = response.read()
        return json.loads(buffer.decode("utf-8"))

    async def buffer(self):
        response = urllib.request.urlopen(self.private_url)
        return response.read()
