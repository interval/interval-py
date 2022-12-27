from dataclasses import dataclass, field
from inspect import isfunction
from typing import Callable

from .action import Action
from ..internal_rpc_schema import AccessControlDefinition
from ..handlers import IntervalActionHandler, IntervalPageHandler


@dataclass
class Page:
    name: str
    description: str | None = None
    unlisted: bool = False
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

    def handle(self, handler: IntervalPageHandler):
        self.handler = handler

    def action(
        self,
        handler_or_slug: IntervalActionHandler | str | None = None,
        *,
        slug: str | None = None,
        name: str | None = None,
        description: str | None = None,
        backgroundable: bool = False,
        unlisted: bool = False,
        access: AccessControlDefinition | None = None,
    ) -> Callable[[IntervalActionHandler], None]:
        def action_adder(handler: IntervalActionHandler):
            self.routes[
                slug
                if slug is not None
                else handler_or_slug
                if (handler_or_slug is not None and isinstance(handler_or_slug, str))
                else handler.__name__
            ] = Action(
                handler=handler,
                name=name,
                description=description,
                backgroundable=backgroundable,
                unlisted=unlisted,
                access=access,
            )

        if handler_or_slug is not None and isfunction(handler_or_slug):
            action_adder(handler_or_slug)

        return action_adder

    def page(
        self,
        name: str,
        slug: str | None = None,
        description: str | None = None,
        unlisted: bool = False,
        access: AccessControlDefinition | None = None,
    ) -> Callable[[IntervalPageHandler], None]:
        def page_adder(handler: IntervalPageHandler):
            self.routes[slug if slug is not None else handler.__name__] = Page(
                handler=handler,
                name=name,
                description=description,
                unlisted=unlisted,
                access=access,
            )

        return page_adder
