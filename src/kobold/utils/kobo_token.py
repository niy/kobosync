import base64
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Self

import orjson

if TYPE_CHECKING:
    from fastapi import Request


@dataclass
class KoboSyncToken:
    lastSuccessfulSyncPointId: str | None = None
    ongoingSyncPointId: str | None = None
    rawKoboSyncToken: str | None = None

    @classmethod
    def from_base64(cls, token_str: str) -> Self:
        try:
            json_bytes = base64.b64decode(token_str)
            data = orjson.loads(json_bytes)
            return cls(**data)
        except Exception:
            return cls()

    def to_base64(self) -> str:
        json_bytes = orjson.dumps(asdict(self))
        return base64.b64encode(json_bytes).decode("utf-8")

    @classmethod
    def from_request(cls, request: Request) -> Self:
        header = request.headers.get("X-Kobo-SyncToken")
        if not header:
            return cls()
        return cls.from_base64(header)

    def to_headers(self) -> dict[str, str]:
        return {"X-Kobo-SyncToken": self.to_base64()}
