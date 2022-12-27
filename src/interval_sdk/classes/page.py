from dataclasses import dataclass, field
from typing import Callable

from .action import Action
from ..internal_rpc_schema import AccessControlDefinition
from ..handlers import IntervalPageHandler


@dataclass
class Page:
    name: str
    description: str | None = None
    unlisted = False
    routes: dict[str, "Action | Page"] = field(default_factory=dict)
    handler: IntervalPageHandler | None = None
    access: AccessControlDefinition | None = None

    _on_change: Callable[[], None] | None = None

    def add(self, slug: str, route: "Action | Page"):
        self.routes[slug] = route
        if isinstance(route, Page):
            route._on_change = self._handle_change

        self._handle_change

    def remove(self, slug: str):
        try:
            route = self.routes[slug]
            if isinstance(route, Page):
                route._on_change = None

            del self.routes[slug]

            self._handle_change()
        except KeyError:
            pass

    def _handle_change(self):
        if self._on_change is not None:
            self._on_change()
