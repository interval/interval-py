from __future__ import annotations
from dataclasses import dataclass
from typing import ParamSpec, Awaitable

from .io_schema import *
from .component import IOPromise, Component, ComponentRenderer


class IO:
    @dataclass
    class Input:
        _renderer: ComponentRenderer

        def text(
            self,
            label: str,
            help_text: str | None = None,
            default_value: str | None = None,
            multiline: bool | None = None,
            lines: int | None = None,
        ) -> IOPromise[Literal["INPUT_TEXT"], str]:
            c = Component(
                method_name="INPUT_TEXT",
                label=label,
                initial_props=InputTextProps(
                    help_text=help_text,
                    default_value=default_value,
                    multiline=multiline,
                    lines=lines,
                ).dict(),
            )
            return IOPromise(c, renderer=self._renderer)

    @dataclass
    class Select:
        _renderer: ComponentRenderer

    @dataclass
    class Display:
        _renderer: ComponentRenderer

    @dataclass
    class Experimental:
        _renderer: ComponentRenderer

        @dataclass
        class Progress:
            _renderer: ComponentRenderer

    renderer: ComponentRenderer
    input: Input
    select: Select
    display: Display
    experimental: Experimental

    def __init__(
        self,
        renderer: ComponentRenderer,
        group: Callable[[list[IOPromise]], Awaitable[list[Any]]],
    ):
        self.renderer = renderer
        self.input = self.Input(renderer)
        self.select = self.Select(renderer)
        self.display = self.Display(renderer)
        self.experimental = self.Experimental(renderer)
        self.group = group
