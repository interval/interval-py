from dataclasses import dataclass

from .io_schema import *
from .component import IOPromise, Component, ComponentRenderer


class IO:
    @dataclass
    class Input:
        _renderer: ComponentRenderer

        def __init__(self, renderer: ComponentRenderer):
            self._renderer = renderer

        def text(
            self,
            label: str,
            help_text: str | None = None,
            default_value: str | None = None,
            multiline: bool | None = None,
            lines: int | None = None,
        ) -> IOPromise:
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

    class Select:
        pass

    class Display:
        pass

    class Experimental:
        pass

        class Progress:
            pass

    renderer: ComponentRenderer
    input: Input

    def __init__(self, renderer: ComponentRenderer):
        self.renderer = renderer
        self.input = self.Input(renderer)
