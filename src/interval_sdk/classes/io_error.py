from typing import Optional

from typing_extensions import Literal

IOErrorKind = Literal["CANCELED", "TRANSACTION_CLOSED"]


class IOError(Exception):
    kind: IOErrorKind
    message: Optional[str]

    def __init__(self, kind: IOErrorKind, message: Optional[str] = None):
        super()
        self.kind = kind
        self.message = message
