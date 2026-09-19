"""API-key resolution order (argument, environment, credentials file), the request-URL
character guard applied to whatever is found, and the secret-safety invariant that a key
never rides along in an error message or its cause chain."""

from __future__ import annotations

import json
import os

import pytest

from pykosis._config import resolve_api_key
from pykosis.exceptions import KOSISConfigError

VALID_API_KEY = "kosis-api-key-0123456789abcdef"  # a well-formed KOSIS key (ASCII)


def _point_config_at(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("KOSIS_API_KEY", raising=False)
    return tmp_path / "pykosis" / "credentials.json"


def _write_credentials_file(path, contents):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")


def _assert_secret_safe(error, secret):
    seen = set()
    pending = [error]
    while pending:
        current = pending.pop()
        if current is None or id(current) in seen:
            continue
        seen.add(id(current))
        assert secret not in str(current)
        assert secret not in repr(current)
        pending.extend([current.__cause__, current.__context__])


def test_explicit_argument_wins(tmp_path, monkeypatch):
    path = _point_config_at(tmp_path, monkeypatch)
    _write_credentials_file(path, json.dumps({"KOSIS_API_KEY": "FROMFILE"}))
    monkeypatch.setenv("KOSIS_API_KEY", "FROMENV")
    assert resolve_api_key("EXPLICIT") == "EXPLICIT"


def test_environment_used_when_no_argument(tmp_path, monkeypatch):
    path = _point_config_at(tmp_path, monkeypatch)
    _write_credentials_file(path, json.dumps({"KOSIS_API_KEY": "FROMFILE"}))
    monkeypatch.setenv("KOSIS_API_KEY", "FROMENV")
    assert resolve_api_key(None) == "FROMENV"


def test_file_used_when_no_argument_or_env(tmp_path, monkeypatch):
    path = _point_config_at(tmp_path, monkeypatch)
    _write_credentials_file(path, json.dumps({"KOSIS_API_KEY": "FROMFILE"}))
    assert resolve_api_key(None) == "FROMFILE"


def test_no_key_anywhere_raises_config_error_naming_the_store(tmp_path, monkeypatch):
    path = _point_config_at(tmp_path, monkeypatch)  # no file written
    with pytest.raises(KOSISConfigError, match="no KOSIS API key") as caught:
        resolve_api_key(None)
    # The message points at the real store (store_location(), redirect-aware);
    # that is the flat credentials path.
    assert str(path) in str(caught.value)


@pytest.mark.parametrize(
    "contents",
    ["{not json", '["not", "an", "object"]', json.dumps({"KOSIS_API_KEY": 123})],
)
def test_malformed_credentials_file_is_rejected(tmp_path, monkeypatch, contents):
    # Not-JSON, a non-object, or a non-string value all reach the caller as a config
    # error rather than a silent skip -- credbox validates the store and its fault is
    # translated to KOSISConfigError.
    path = _point_config_at(tmp_path, monkeypatch)
    _write_credentials_file(path, contents)
    with pytest.raises(KOSISConfigError, match="could not read"):
        resolve_api_key(None)


def test_unreadable_credentials_file_raises_config_error(tmp_path, monkeypatch):
    path = _point_config_at(tmp_path, monkeypatch)
    path.mkdir(parents=True)  # a directory where the file should be -> OSError on read
    with pytest.raises(KOSISConfigError, match="could not read"):
        resolve_api_key(None)


def test_blank_file_key_is_treated_as_absent(tmp_path, monkeypatch):
    path = _point_config_at(tmp_path, monkeypatch)
    _write_credentials_file(path, json.dumps({"KOSIS_API_KEY": ""}))
    with pytest.raises(KOSISConfigError, match="no KOSIS API key"):  # blank == absent
        resolve_api_key(None)


@pytest.mark.parametrize("blank_source", ["explicit", "environment"])
def test_blank_higher_tier_falls_through_to_the_file(
    tmp_path, monkeypatch, blank_source
):
    # A blank explicit argument or env var is "absent" (credbox trims to empty), so
    # resolution falls through to the file rather than returning empty.
    path = _point_config_at(tmp_path, monkeypatch)
    _write_credentials_file(path, json.dumps({"KOSIS_API_KEY": VALID_API_KEY}))
    explicit = None
    if blank_source == "explicit":
        explicit = "   "
    else:
        monkeypatch.setenv("KOSIS_API_KEY", "   ")

    assert resolve_api_key(explicit) == VALID_API_KEY


@pytest.mark.parametrize("source", ["explicit", "environment", "stored"])
def test_key_is_trimmed_at_every_tier(tmp_path, monkeypatch, source):
    # credbox strips surrounding whitespace at every tier (a pasted trailing newline no
    # longer breaks auth); pinned so a future change cannot silently return padding.
    path = _point_config_at(tmp_path, monkeypatch)
    padded = "  " + VALID_API_KEY + "  "
    explicit = None
    if source == "explicit":
        explicit = padded
    elif source == "environment":
        monkeypatch.setenv("KOSIS_API_KEY", padded)
    else:
        _write_credentials_file(path, json.dumps({"KOSIS_API_KEY": padded}))

    assert resolve_api_key(explicit) == VALID_API_KEY


@pytest.mark.parametrize(
    "bad_key",
    [
        "prefix\nSECRETTAIL",  # a control character
        "prefix한SECRETTAIL",  # a non-ASCII character
        "prefix\udcfeSECRETTAIL",  # a lone surrogate (corrupt environment bytes)
    ],
)
def test_key_outside_printable_ascii_raises_and_never_echoes_the_key(
    tmp_path, monkeypatch, bad_key
):
    # credbox trims surrounding whitespace but keeps a control character, a non-ASCII
    # character, or a lone surrogate. KOSIS url-encodes the key into the query, and a
    # surrogate makes urllib.parse.urlencode raise a whole-key error. Reject it as a
    # config error, echoing nothing -- not the message, not anywhere in the cause chain.
    _point_config_at(tmp_path, monkeypatch)
    with pytest.raises(KOSISConfigError, match="printable ASCII") as exc:
        resolve_api_key(bad_key)
    _assert_secret_safe(exc.value, "prefix")
    _assert_secret_safe(exc.value, "SECRETTAIL")


@pytest.mark.skipif(not hasattr(os, "environb"), reason="bytes environment required")
def test_surrogate_environment_key_raises_without_echoing(tmp_path, monkeypatch):
    # The real threat: KOSIS_API_KEY holds invalid-UTF-8 bytes, which os.environ
    # decodes with surrogateescape into a lone surrogate. credbox preserves it, and the
    # guard must reject it before urllib.parse.urlencode raises a whole-key error.
    _point_config_at(tmp_path, monkeypatch)
    monkeypatch.setitem(os.environb, b"KOSIS_API_KEY", b"prefix\xfeSECRETTAIL")
    with pytest.raises(KOSISConfigError, match="printable ASCII") as caught:
        resolve_api_key(None)
    _assert_secret_safe(caught.value, "prefix")
    _assert_secret_safe(caught.value, "SECRETTAIL")


def test_store_binding_redirects_to_a_host_namespace(tmp_path, monkeypatch):
    # A host embedding pykosis redirects the store via PYKOSIS_STORE_APP +
    # PYKOSIS_NAMESPACE, so pykosis's key lives in the host store's pykosis section.
    _point_config_at(tmp_path, monkeypatch)
    monkeypatch.setenv("PYKOSIS_STORE_APP", "host")
    monkeypatch.setenv("PYKOSIS_NAMESPACE", "kosis")
    host = tmp_path / "host"
    host.mkdir(parents=True)
    (host / "credentials.json").write_text(
        json.dumps({"kosis": {"KOSIS_API_KEY": VALID_API_KEY}}), encoding="utf-8"
    )

    assert resolve_api_key(None) == VALID_API_KEY


@pytest.mark.parametrize("source", ["explicit", "environment"])
def test_higher_tier_wins_before_an_invalid_binding_is_validated(monkeypatch, source):
    # An explicit argument or KOSIS_API_KEY resolves before the binding is validated
    # (lazy), so a bad binding never raises when a higher tier supplies the key.
    monkeypatch.delenv("KOSIS_API_KEY", raising=False)
    monkeypatch.setenv("PYKOSIS_STORE_APP", "../invalid")
    explicit = None
    if source == "explicit":
        explicit = VALID_API_KEY
    else:
        monkeypatch.setenv("KOSIS_API_KEY", VALID_API_KEY)

    assert resolve_api_key(explicit) == VALID_API_KEY


def test_invalid_store_binding_raises_config_error(monkeypatch):
    # A malformed binding surfaces as pykosis's KOSISConfigError on first store touch.
    monkeypatch.delenv("KOSIS_API_KEY", raising=False)
    monkeypatch.setenv("PYKOSIS_STORE_APP", "../invalid")
    with pytest.raises(KOSISConfigError, match="could not read"):
        resolve_api_key(None)


@pytest.mark.parametrize(
    "contents",
    [
        lambda secret: secret.encode() + b"\xff",  # not valid UTF-8
        lambda secret: (secret + "{").encode(),  # not valid JSON
        lambda secret: json.dumps([secret]).encode(),  # a JSON array, not an object
        lambda secret: json.dumps({"KOSIS_API_KEY": [secret]}).encode(),  # non-string
    ],
)
def test_malformed_store_detaches_secret_bearing_context(
    tmp_path, monkeypatch, contents
):
    # Whatever the fault, the key bytes must not ride along in the error, its repr, or
    # the cause chain -- credbox detaches secret-bearing content and `from err` keeps
    # that, the load-bearing secret-safety invariant.
    secret = "kosis-secret-value-abcdef"
    path = _point_config_at(tmp_path, monkeypatch)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(contents(secret))
    with pytest.raises(KOSISConfigError, match="could not read") as caught:
        resolve_api_key(None)
    _assert_secret_safe(caught.value, secret)


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits required")
def test_loose_permission_file_warns_and_still_reads(tmp_path, monkeypatch, capsys):
    # A group/other-readable file is warned about (chmod 600 nudge), not refused.
    path = _point_config_at(tmp_path, monkeypatch)
    _write_credentials_file(path, json.dumps({"KOSIS_API_KEY": VALID_API_KEY}))
    path.chmod(0o644)

    assert resolve_api_key(None) == VALID_API_KEY
    assert "chmod 600" in capsys.readouterr().err
