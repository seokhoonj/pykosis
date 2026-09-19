"""Resolve the KOSIS API key from the caller, the environment, or the config file.

The key is looked up in a fixed order, so an explicit value always wins and a set
environment variable beats a file on disk:

1. the ``api_key`` passed to ``KOSIS(...)``
2. the ``KOSIS_API_KEY`` environment variable
3. ``"KOSIS_API_KEY"`` in ``$XDG_CONFIG_HOME/pykosis/credentials.json``
   (``$XDG_CONFIG_HOME`` defaults to ``~/.config``)

The environment variable name matches the R ``kosis`` package, so a key already in a
shell is picked up unchanged. The resolution, the whitespace trimming, the permission
handling (a group/other-readable file is warned about, not refused), and the storage
backend are delegated to credbox. The store binding is not hardcoded:
``Credentials.for_app("pykosis")`` lets a host embedding pykosis redirect it via
``PYKOSIS_STORE_APP`` / ``PYKOSIS_NAMESPACE``; standalone it is exactly the flat
``~/.config/pykosis/credentials.json`` pykosis has always read. A file present but
unreadable, not JSON, or not a JSON object is still an error rather than a silent skip.

Once a key is found, any character outside printable ASCII is rejected here. A
KOSIS key is plain ASCII, so a control char, a non-ASCII char, or a lone surrogate (from
corrupt environment bytes) can only be a broken key -- and a lone surrogate additionally
makes ``urllib.parse.urlencode`` raise a whole-key ``UnicodeEncodeError`` while encoding
the key into the query string, echoing it. That check is pykosis's own concern, not
something the credential store knows about.
"""

from __future__ import annotations

from functools import lru_cache

from credbox import CredBoxError, Credentials

from .exceptions import KOSISConfigError

_ENV_VAR = "KOSIS_API_KEY"
_STORE_APP = "pykosis"


def resolve_api_key(explicit: str | None) -> str:
    """Return the first key found across the three sources, or raise if none exists."""
    try:
        found = _get_credentials().secret(_ENV_VAR, override=explicit)
    except CredBoxError as err:
        # credbox's message already names the store path + fault; don't prepend a static
        # path (wrong under a PYKOSIS_STORE_APP redirect); credbox detaches the
        # secret-bearing context, so `from err` keeps the key out of any traceback.
        raise KOSISConfigError(f"could not read the credential store: {err}") from err
    if found is None:
        # Binding validated cleanly above (None, not error), so store_location() is safe
        # and gives the real store (the host's under a redirect).
        raise KOSISConfigError(
            f"no KOSIS API key: pass api_key=, set the {_ENV_VAR} environment "
            f"variable, or put it in {_get_credentials().store_location()}"
        )
    key = found.reveal()
    if any(not (0x20 <= ord(ch) < 0x7F) for ch in key):
        # A KOSIS key is plain ASCII, so any character outside printable ASCII -- a
        # control char, a non-ASCII char, or a lone surrogate from corrupt environment
        # bytes -- can only be a broken key. A lone surrogate additionally makes
        # ``urllib.parse.urlencode`` raise a whole-key ``UnicodeEncodeError`` while
        # encoding it into the query string, echoing the key -- so reject it here,
        # before it becomes a request, and never echo it.
        raise KOSISConfigError(
            "the KOSIS API key must be printable ASCII (a stray newline, tab, or "
            "non-ASCII character is a broken key)"
        )
    return key


@lru_cache(maxsize=1)
def _get_credentials() -> Credentials:
    """pykosis's credbox credential store, built on first use and cached.

    Built via ``for_app`` (not bare ``Credentials(...)``) so a host embedding pykosis
    can redirect the binding with ``PYKOSIS_STORE_APP`` / ``PYKOSIS_NAMESPACE`` before
    the first lookup. credbox re-resolves the store *path* per call (honouring a later
    ``XDG_CONFIG_HOME``); the binding is read from the environment once, when the facade
    is built. A malformed binding surfaces as ``KOSISConfigError`` on the first lookup
    that reaches the store -- an explicit arg or ``KOSIS_API_KEY`` resolves first, so a
    bad binding with the env var set never raises.
    """
    return Credentials.for_app(_STORE_APP)
