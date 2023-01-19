import asyncio
import sys, traceback
from typing import Optional
from typing_extensions import TypeAlias, Literal

from ..types import BaseModel

LogLevel: TypeAlias = Literal["quiet", "info", "debug"]

CHANGELOG_URL = "https://interval.com/changelog"

WARN_EMOJI = "\u26A0\uFE0F"
ERROR_EMOJI = "‼️"


class SdkAlert(BaseModel):
    min_sdk_version: str
    severity: Literal["INFO", "WARNING", "ERROR"]
    message: Optional[str] = None


class Logger:
    prefix: str = "Interval"
    log_level: LogLevel = "info"

    def __init__(
        self,
        log_level: Optional[LogLevel] = None,
        prefix: Optional[str] = None,
    ):
        if log_level is not None:
            self.log_level = log_level
        if prefix is not None:
            self.prefix = prefix

    def prod(self, *args, **kwargs):
        """Important messages, always emitted"""
        print(f"[{self.prefix}] ", *args, **kwargs)

    def prod_no_prefix(self, *args, **kwargs):
        """Same as prod, but without the [Interval] prefix"""
        print(*args, **kwargs)

    def error(self, *args, **kwargs):
        """Fatal errors or errors in user code, always emitted"""
        print(f"[{self.prefix}] ", *args, **kwargs, file=sys.stderr)

    def info(self, *args, **kwargs):
        """Informational messages, not emitted in "quiet" log level"""
        if self.log_level != "quiet":
            print(f"[{self.prefix}] ", *args, **kwargs)

    def info_no_prefix(self, *args, **kwargs):
        """Same as info, but without the [Interval] prefix"""
        if self.log_level != "quiet":
            print(*args, **kwargs)

    def warn(self, *args, **kwargs):
        """Non-fatal warnings, not emitted in "quiet" log level"""
        if self.log_level != "quiet":
            print(f"[{self.prefix}] ", *args, **kwargs, file=sys.stderr)

    def debug(self, *args, **kwargs):
        """Debugging/tracing information, only emitted in "debug" log level"""
        if self.log_level == "debug":
            print(f"[{self.prefix}] ", *args, **kwargs)

    def print_exception(self, err: Optional[BaseException] = None):
        if self.log_level == "debug":
            traceback.print_exc(file=sys.stderr)

    def handle_sdk_alert(self, sdk_alert: SdkAlert):
        self.info_no_prefix()

        if sdk_alert.severity == "INFO":
            self.info("🆕\tA new Interval SDK version is available.")
            if sdk_alert.message:
                self.info(sdk_alert.message)
        elif sdk_alert.severity == "WARNING":
            self.warn(
                f"{WARN_EMOJI}\tThis version of the Interval SDK has been deprecated. Please update as soon as possible, it will not work in a future update."
            )
            if sdk_alert.message:
                self.warn(sdk_alert.message)
            pass
        elif sdk_alert.severity == "ERROR":
            self.error(
                f"{ERROR_EMOJI}\tThis version of the Interval SDK is no longer supported. Your app will not work until you update."
            )
            if sdk_alert.message:
                self.error(sdk_alert.message)
            pass
        elif sdk_alert.message:
            self.prod(sdk_alert.message)

        self.info("\t- See what's new at:", CHANGELOG_URL)

        self.info_no_prefix()

    def handle_task_exceptions(self, task: asyncio.Task):
        try:
            task.result()
        except BaseException as err:
            self.error(err)
