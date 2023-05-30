from typing import Optional

from typing_extensions import Literal

IOErrorKind = Literal[
    "CANCELED",
    "TRANSACTION_CLOSED",
    "BAD_RESPONSE",
    "RESPONSE_HANDLER_ERROR",
    "RENDER_ERROR",
]


class IOError(Exception):
    kind: IOErrorKind
    message: Optional[str]

    def __init__(self, kind: IOErrorKind, message: Optional[str] = None):
        super()
        self.kind = kind
        self.message = message

    def __str__(self):
        if self.message is not None:
            return self.message

        return self.kind
