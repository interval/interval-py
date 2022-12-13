from typing import Literal

IOErrorKind = Literal["CANCELED", "TRANSACTION_CLOSED"]


class IOError(Exception):
    kind: IOErrorKind
    message: str | None

    def __init__(self, kind: IOErrorKind, message: str | None = None):
        super()
        self.kind = kind
        self.message = message
