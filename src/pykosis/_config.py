"""Resolve the KOSIS API key from the caller, the environment, or the config file.

The key is looked up in a fixed order, so an explicit value always wins and a set
environment variable beats a file on disk:

1. the ``api_key`` passed to ``KOSIS(...)``
2. the ``KOSIS_API_KEY`` environment variable
3. ``"KOSIS_API_KEY"`` in ``$XDG_CONFIG_HOME/pykosis/credentials.json``
   (``$XDG_CONFIG_HOME`` defaults to ``~/.config``)

The environment variable name matches the R ``kosis`` package, so a key already in
``.Renviron``-style shells is picked up unchanged. The file is optional -- its absence
just means "no key here." But a file that is present and unreadable, not JSON, or not a
JSON object is an error, because a caller who wrote one meant it to be used and a silent
skip would hide the mistake.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .exceptions import KOSISConfigError

_ENV_VAR = "KOSIS_API_KEY"
_CONFIG_DIR = "pykosis"
_CONFIG_FILE = "credentials.json"


def resolve_api_key(explicit: str | None) -> str:
    """Return the first key found across the three sources, or raise if none exists."""
    key = explicit or os.environ.get(_ENV_VAR) or _key_from_file()
    if not key:
        raise KOSISConfigError(
            f"no KOSIS API key: pass api_key=, set the {_ENV_VAR} environment "
            f"variable, or put it in {credentials_path()}"
        )
    return key


def credentials_path() -> Path:
    """The path pykosis reads a stored key from (honoring ``$XDG_CONFIG_HOME``)."""
    config_home = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(config_home) / _CONFIG_DIR / _CONFIG_FILE


def _key_from_file() -> str | None:
    path = credentials_path()
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as err:
        raise KOSISConfigError(f"could not read {path}: {err}") from err

    try:
        credentials = json.loads(text)
    except json.JSONDecodeError as err:
        raise KOSISConfigError(f"{path} is not valid JSON: {err}") from err
    if not isinstance(credentials, dict):
        raise KOSISConfigError(f"{path} must contain a JSON object")

    key = credentials.get(_ENV_VAR)
    return key if isinstance(key, str) and key else None
