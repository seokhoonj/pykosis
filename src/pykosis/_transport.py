"""One request over the wire: build the KOSIS query URL, GET it, surface errors.

Unlike the Bank of Korea ECOS API (positional path segments), KOSIS is a
query-string API: each service has its own base URL and takes named parameters:

    {base_url}?method=getList&apiKey=...&format=json&jsonVD=Y&...

``_Transport`` holds the HTTP client and the pacing clock. It spaces consecutive
requests (``delay_seconds``) so a burst stays under the KOSIS cap of 200 calls per
minute, and retries a transient failure (timeout, connection reset, 5xx) with backoff.

KOSIS signals a *vendor* error not with an HTTP status but with a JSON object
``{"err": "<code>", "errMsg": "<text>"}`` in an otherwise-200 response; a successful
call returns a JSON *array* of row objects instead. This module tells the two apart and
raises the object form through the :class:`KOSISError` hierarchy.
"""

from __future__ import annotations

import json
import time
from typing import Any
from urllib.parse import urlencode

import httpx

from .exceptions import (
    KOSISAuthError,
    KOSISNetworkError,
    KOSISRateLimitError,
    KOSISResponseError,
)

# The vendor caps a single call at 40,000 cells and the account at 200 calls/minute;
# neither is an HTTP header, so pacing (delay_seconds) is the client's only lever.
# A transient failure (timeout, reset, 5xx) is a glitch worth retrying. This counts
# total attempts, not retries -- 3 is one try plus two retries.
_MAX_ATTEMPTS = 3
_RETRY_BACKOFF_SECONDS = 1.0
_RETRY_BACKOFF_FACTOR = 2  # each retry waits this many times the last

# Vendor error codes confirmed by live calls. A rejected key is err "11" ("유효하지 않은
# 인증KEY입니다."); a query that matches nothing is err "30" ("데이터가 존재하지
# 않습니다.") -- an empty result, not a failure, so it maps to []. Other codes seen:
# "20" (a required objL is missing), "21" (no such table); both stay response errors.
_AUTH_ERR_CODES = frozenset({"11"})
_NO_DATA_CODE = "30"


class _Transport:
    """The HTTP client plus its pacing clock -- one per :class:`KOSIS`.

    ``delay_seconds`` spaces consecutive requests so a burst (many tables in a loop)
    stays under the KOSIS cap of 200 calls per minute; the default is 0 because a
    handful of calls never reaches it, and pacing every call would only slow the common
    case. A bulk caller sets it -- 0.3s keeps one client under the per-minute cap
    indefinitely.

    Not thread-safe: the pacing clock (``_next_request_at``) is shared mutable state, so
    use one client -- hence one transport -- per thread.
    """

    def __init__(
        self,
        client: httpx.Client,
        *,
        delay_seconds: float = 0.0,
        max_attempts: int = _MAX_ATTEMPTS,
    ) -> None:
        self._client = client
        self._delay_seconds = delay_seconds
        self._max_attempts = max_attempts
        self._next_request_at = 0.0

    def request(self, *, base_url: str, params: dict[str, str]) -> list[dict[str, Any]]:
        """Fetch one call and return its rows as a list of raw vendor dicts.

        Retries a transient transport failure (timeout, connection reset, 5xx) with
        backoff. Raises :class:`KOSISNetworkError` if it never completes,
        :class:`KOSISAuthError` on a rejected key, :class:`KOSISResponseError` on any
        other vendor error (the ``{"err", "errMsg"}`` object form). A query that simply
        matches no data returns an empty list.
        """
        url = f"{base_url}?{urlencode(params)}"
        last_error: KOSISNetworkError | None = None
        for attempt in range(self._max_attempts):
            self._wait_for_next_slot()
            try:
                response = self._client.get(url)
                response.raise_for_status()
                payload = response.json()
            except httpx.HTTPStatusError as err:
                # Message from the status line ONLY. ``str(err)`` -- and the httpx
                # exception chained as a cause -- embed the request URL, which carries
                # ``apiKey=<key>``. Never surface either; ``from None`` also keeps that
                # URL out of a printed traceback.
                status = err.response.status_code
                detail = f"HTTP {status} {err.response.reason_phrase}".rstrip()
                if status == 429:  # Too Many Requests -- the rate cap, not retried
                    raise KOSISRateLimitError("429", detail) from None
                if status < 500:  # any other 4xx is the server's answer
                    raise KOSISNetworkError(detail) from None
                last_error = KOSISNetworkError(detail)  # 5xx: retry
            except httpx.HTTPError as err:  # timeout, connection reset, ...
                # Report the failure kind, not ``str(err)``/the cause -- same reason.
                last_error = KOSISNetworkError(f"request failed ({type(err).__name__})")
            except json.JSONDecodeError as err:
                # A 200 whose body is not JSON (a proxy/maintenance HTML page) must
                # surface through the KOSISError hierarchy, not as a raw decode error.
                # Safe to chain: a decode error is about the response body, not the
                # key-bearing request URL.
                raise KOSISResponseError(
                    "UNKNOWN", f"non-JSON response from KOSIS: {err}") from err
            else:
                return _extract_rows(payload)
            if attempt + 1 < self._max_attempts:
                time.sleep(_RETRY_BACKOFF_SECONDS * _RETRY_BACKOFF_FACTOR**attempt)
        if last_error is not None:
            raise last_error
        raise KOSISNetworkError("request failed")

    def _wait_for_next_slot(self) -> None:
        if self._delay_seconds <= 0:
            return
        now = time.monotonic()
        if now < self._next_request_at:
            time.sleep(self._next_request_at - now)
        self._next_request_at = time.monotonic() + self._delay_seconds


def _extract_rows(payload: Any) -> list[dict[str, Any]]:
    """A KOSIS payload as a list of row dicts, or raise on the vendor error object.

    Success is a JSON array of row objects; a vendor error is a JSON object carrying
    ``err`` / ``errMsg``. A "no matching data" error (``err`` "30") is not a failure --
    it returns an empty list. A lone object without ``err`` is treated as a single-row
    result (some services return one record unwrapped).
    """
    if isinstance(payload, dict):
        if "err" in payload or "errMsg" in payload:
            code = str(payload.get("err", "UNKNOWN"))
            message = str(payload.get("errMsg", ""))
            if code == _NO_DATA_CODE:  # no matching data -- empty result, not a failure
                return []
            if code in _AUTH_ERR_CODES:
                raise KOSISAuthError(code, message or "invalid KOSIS API key")
            raise KOSISResponseError(code, message)
        return [payload]  # a single unwrapped record
    if isinstance(payload, list):
        rows = [row for row in payload if isinstance(row, dict)]
        if len(rows) != len(payload):
            raise KOSISResponseError(
                "UNKNOWN", f"unexpected KOSIS response: {payload!r}")
        return rows
    raise KOSISResponseError("UNKNOWN", f"unexpected KOSIS response: {payload!r}")
