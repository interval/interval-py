from dataclasses import dataclass

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
    ):
        self.renderer = renderer
        self.input = self.Input(renderer)
        self.select = self.Select(renderer)
        self.display = self.Display(renderer)
        self.experimental = self.Experimental(renderer)

    # TODO: Generate generic stubs for up to a certain number of args
    # https://github.com/python/typeshed/blob/4d23919200d9e89486f4d9e2587f82314d4af0f6/stdlib/asyncio/tasks.pyi#L82-L165
    async def group(self, io_promises: list[IOPromise]) -> list[Any]:
        return await self.renderer([p.component for p in io_promises])
