"""Exception hierarchy for pykosis.

Every *operational* error raised by this package derives from ``KOSISError``, so a
caller can catch all of them with one ``except KOSISError``. The subclasses separate
the failure modes a caller handles differently: a misconfiguration caught before any
request, a rejected API key, a vendor-reported error inside a well-formed response,
and a transport failure that never reached KOSIS. An *invalid argument* -- an unknown
``frequency`` or ``view_code`` value -- raises the standard ``ValueError`` instead, the
usual signal for a caller mistake rather than a runtime failure.
"""

from __future__ import annotations


class KOSISError(Exception):
    """Base class for every error raised by pykosis."""


class KOSISConfigError(KOSISError):
    """The client is misconfigured; raised before any request goes out.

    The usual cause is a missing API key -- neither passed to ``KOSIS(...)`` nor
    present in the ``KOSIS_API_KEY`` environment variable nor the credentials file.
    """


class KOSISResponseError(KOSISError):
    """KOSIS returned a well-formed response carrying an error code.

    KOSIS reports a failure as a JSON object ``{"err": "<code>", "errMsg": "<text>"}``
    rather than an HTTP error status; ``code`` and ``message`` are the vendor's own,
    so a caller can branch on the code without parsing the message text. A common one
    is ``err=20`` (a required ``objL`` classification is missing) -- widen the query by
    setting the next ``obj_l*`` to ``"ALL"``. ``code`` is the vendor ``err`` code except
    ``"429"`` (an HTTP rate limit, on :class:`KOSISRateLimitError`) and ``"UNKNOWN"`` (a
    malformed or non-JSON response).
    """

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class KOSISAuthError(KOSISResponseError):
    """KOSIS rejected the API key.

    Subclasses :class:`KOSISResponseError` so it carries the vendor ``code``/``message``
    and ``except KOSISResponseError`` catches it, while a caller can still catch an auth
    failure distinctly.
    """


class KOSISRateLimitError(KOSISResponseError):
    """KOSIS is rate-limiting the caller.

    KOSIS caps a key at 200 calls per minute. This is raised on an HTTP 429 (Too Many
    Requests). It subclasses :class:`KOSISResponseError`, so ``except
    KOSISResponseError`` still catches it, but a caller can catch this distinctly to
    back off and retry rather than fail. (KOSIS's exact rate-limit error *body*, if sent
    instead of a 429, is undocumented and not mapped yet -- pace requests with
    ``delay_seconds`` to stay under the cap.)
    """


class KOSISNetworkError(KOSISError):
    """The request failed at the transport or HTTP layer.

    A timeout, DNS failure, connection reset, or a non-success HTTP status that KOSIS
    never turned into an error body. The underlying exception is chained as
    ``__cause__``.
    """
