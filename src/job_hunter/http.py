from __future__ import annotations

import json
from typing import Any, Optional
from urllib.error import URLError
from urllib import parse, request


class HttpError(RuntimeError):
    pass


def get_json(url: str, headers: Optional[dict[str, str]] = None) -> Any:
    try:
        req = request.Request(url, headers=headers or {})
        with request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except URLError as exc:
        raise HttpError(str(exc)) from exc


def post_json(url: str, payload: dict[str, Any], headers: Optional[dict[str, str]] = None) -> Any:
    merged_headers = {"Content-Type": "application/json"}
    if headers:
        merged_headers.update(headers)
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=merged_headers,
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=30) as resp:
            body = resp.read()
            if not body:
                return None
            decoded = body.decode("utf-8")
            try:
                return json.loads(decoded)
            except json.JSONDecodeError:
                return decoded
    except URLError as exc:
        raise HttpError(str(exc)) from exc


def build_url(base: str, params: dict[str, Any]) -> str:
    clean = {key: value for key, value in params.items() if value not in (None, "", [])}
    return f"{base}?{parse.urlencode(clean, doseq=True)}"
