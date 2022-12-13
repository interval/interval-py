import sys, traceback
from typing import TypeAlias, Literal

LogLevel: TypeAlias = Literal["prod", "debug"]


class Logger:
    log_level: LogLevel = "prod"

    def __init__(self, log_level: LogLevel = "prod"):
        self.log_level = log_level

    def prod(self, *args, **kwargs):
        print("[Interval]", *args, **kwargs)

    def warn(self, *args, **kwargs):
        print(*args, **kwargs, file=sys.stderr)

    def error(self, *args, **kwargs):
        print(*args, **kwargs, file=sys.stderr)

    def debug(self, *args, **kwargs):
        if self.log_level == "debug":
            print(*args, **kwargs)

    def print_exception(self, err: Exception):
        if self.log_level == "debug":
            traceback.print_exception(err, file=sys.stderr)
