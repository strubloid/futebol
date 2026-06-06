from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx


@dataclass(frozen=True, slots=True)
class HttpResponse:
    url: str
    status_code: int
    text: str
    content_type: str | None = None


class TextHttpClient(Protocol):
    def get_text(self, url: str) -> HttpResponse:
        pass


class HttpClient:
    def __init__(self, timeout_seconds: float = 8.0) -> None:
        self._timeout_seconds = timeout_seconds

    def get_text(self, url: str) -> HttpResponse:
        with httpx.Client(follow_redirects=True, timeout=self._timeout_seconds) as client:
            response = client.get(url)
        return HttpResponse(
            url=str(response.url),
            status_code=response.status_code,
            text=response.text,
            content_type=response.headers.get("content-type"),
        )

    def probe(self, url: str) -> HttpResponse:
        with httpx.Client(follow_redirects=True, timeout=self._timeout_seconds) as client:
            response = client.head(url)
            if response.status_code in {405, 403}:
                response = client.get(url, headers={"Range": "bytes=0-256"})
        return HttpResponse(
            url=str(response.url),
            status_code=response.status_code,
            text="",
            content_type=response.headers.get("content-type"),
        )
