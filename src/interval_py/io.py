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

        def email(
            self,
            label: str,
            help_text: str | None = None,
            default_value: str | None = None,
        ) -> IOPromise[Literal["INPUT_EMAIL"], str]:
            c = Component(
                method_name="INPUT_EMAIL",
                label=label,
                initial_props=InputEmailProps(
                    help_text=help_text,
                    default_value=default_value,
                ).dict(),
            )
            return IOPromise(c, renderer=self._renderer)

        def number(
            self,
            label: str,
            min: int | None = None,
            max: int | None = None,
            prepend: str | None = None,
            help_text: str | None = None,
            default_value: str | None = None,
        ) -> IOPromise[Literal["INPUT_NUMBER"], int]:
            c = Component(
                method_name="INPUT_NUMBER",
                label=label,
                initial_props=InputNumberProps(
                    min=min,
                    max=max,
                    prepend=prepend,
                    help_text=help_text,
                    default_value=default_value,
                ).dict(),
            )
            return IOPromise(c, renderer=self._renderer)

        def boolean(
            self,
            label: str,
            help_text: str | None = None,
            default_value: str | None = None,
        ) -> IOPromise[Literal["INPUT_BOOLEAN"], bool]:
            c = Component(
                method_name="INPUT_BOOLEAN",
                label=label,
                initial_props=InputBooleanProps(
                    help_text=help_text,
                    default_value=default_value,
                ).dict(),
            )
            return IOPromise(c, renderer=self._renderer)

        def rich_text(
            self,
            label: str,
            help_text: str | None = None,
        ) -> IOPromise[Literal["INPUT_RICH_TEXT"], str]:
            c = Component(
                method_name="INPUT_RICH_TEXT",
                label=label,
                initial_props=InputRichTextProps(
                    help_text=help_text,
                ).dict(),
            )
            return IOPromise(c, renderer=self._renderer)

        def spreadsheet(
            self,
            label: str,
            columns: dict[str, TypeValue],
            help_text: str | None = None,
        ) -> IOPromise[Literal["INPUT_SPREADSHEET"], list]:
            c = Component(
                method_name="INPUT_SPREADSHEET",
                label=label,
                initial_props=InputSpreadsheetProps(
                    help_text=help_text,
                    columns=columns,
                ).dict(),
            )
            return IOPromise(c, renderer=self._renderer)

    @dataclass
    class Select:
        _renderer: ComponentRenderer

        def table(
            self,
            label: str,
            data: list[TableRow],
            help_text: str | None = None,
            columns: TableColumnDef | None = None,
        ) -> IOPromise[Literal["SELECT_TABLE"], list]:
            c = Component(
                method_name="SELECT_TABLE",
                label=label,
                initial_props=SelectTableProps(
                    help_text=help_text,
                    columns=columns,
                    data=data,
                ).dict(),
            )
            return IOPromise(c, renderer=self._renderer)

        def single(
            self,
            label: str,
            options: list[RichSelectOption],
            help_text: str | None = None,
            default_value: RichSelectOption | None = None,
            searchable: bool | None = None,
        ) -> IOPromise[Literal["SELECT_SINGLE"], RichSelectOption]:
            c = Component(
                method_name="SELECT_SINGLE",
                label=label,
                initial_props=SelectSingleProps(
                    options=options,
                    help_text=help_text,
                    default_value=default_value,
                    searchable=searchable,
                ).dict(),
            )
            return IOPromise(c, renderer=self._renderer)

        def multiple(
            self,
            label: str,
            options: list,
            help_text: str | None = None,
            default_value: list[LabelValue] = [],
        ) -> IOPromise[Literal["SELECT_MULTIPLE"], list]:
            c = Component(
                method_name="SELECT_MULTIPLE",
                label=label,
                initial_props=SelectMultipleProps(
                    options=options,
                    help_text=help_text,
                    default_value=default_value,
                ).dict(),
            )
            return IOPromise(c, renderer=self._renderer)

    @dataclass
    class Display:
        _renderer: ComponentRenderer

        def heading(
            self,
            label: str,
        ) -> IOPromise[Literal["DISPLAY_HEADING"], None]:
            c = Component(
                method_name="DISPLAY_HEADING",
                label=label,
                initial_props={},
            )
            return IOPromise(c, renderer=self._renderer)

        def markdown(
            self,
            label: str,
        ) -> IOPromise[Literal["DISPLAY_MARKDOWN"], None]:
            c = Component(
                method_name="DISPLAY_MARKDOWN",
                label=label,
                initial_props={},
            )
            return IOPromise(c, renderer=self._renderer)

    @dataclass
    class Experimental:
        @dataclass
        class Progress:
            _renderer: ComponentRenderer

            def progress_steps(
                self,
                label: str,
                steps: DisplayProgressStepsSteps,
                current_step: int | None = None,
                subtitle: str | None = None,
            ) -> IOPromise[Literal["DISPLAY_PROGRESS_STEPS"], None]:
                c = Component(
                    method_name="DISPLAY_PROGRESS_STEPS",
                    label=label,
                    initial_props=DisplayProgressStepsProps(
                        steps=steps,
                        current_step=current_step,
                        subtitle=subtitle,
                    ).dict(),
                )
                return IOPromise(c, renderer=self._renderer)

            def progress_indeterminate(
                self,
                label: str,
            ) -> IOPromise[Literal["DISPLAY_PROGRESS_INDETERMINATE"], None]:
                c = Component(
                    method_name="DISPLAY_PROGRESS_INDETERMINATE",
                    label=label,
                    initial_props={},
                )
                return IOPromise(c, renderer=self._renderer)

            def progress_through_list(
                self,
                label: str,
                items: list[DisplayProgressthroughListItem],
            ) -> IOPromise[Literal["DISPLAY_PROGRESS_THROUGH_LIST"], None]:
                c = Component(
                    method_name="DISPLAY_PROGRESS_THROUGH_LIST",
                    label=label,
                    initial_props=DisplayProgressThroughListProps(
                        items=items,
                    ).dict(),
                )
                return IOPromise(c, renderer=self._renderer)

        _renderer: ComponentRenderer
        progress: Progress

        def __init__(self, renderer: ComponentRenderer):
            self._renderer = renderer
            self.progress = IO.Experimental.Progress(renderer)

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
