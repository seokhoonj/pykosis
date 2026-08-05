"""API-key resolution order: argument, environment, then credentials file."""

from __future__ import annotations

import json

import pytest

from pykosis._config import resolve_api_key
from pykosis.exceptions import KOSISConfigError


def test_explicit_argument_wins(monkeypatch):
    monkeypatch.setenv("KOSIS_API_KEY", "FROMENV")
    assert resolve_api_key("EXPLICIT") == "EXPLICIT"


def test_environment_used_when_no_argument(monkeypatch):
    monkeypatch.setenv("KOSIS_API_KEY", "FROMENV")
    assert resolve_api_key(None) == "FROMENV"


def test_file_used_when_no_argument_or_env(monkeypatch, tmp_path):
    monkeypatch.delenv("KOSIS_API_KEY", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config_dir = tmp_path / "pykosis"
    config_dir.mkdir()
    (config_dir / "credentials.json").write_text(
        json.dumps({"KOSIS_API_KEY": "FROMFILE"}), encoding="utf-8")
    assert resolve_api_key(None) == "FROMFILE"


def test_environment_beats_file(monkeypatch, tmp_path):
    monkeypatch.setenv("KOSIS_API_KEY", "FROMENV")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config_dir = tmp_path / "pykosis"
    config_dir.mkdir()
    (config_dir / "credentials.json").write_text(
        json.dumps({"KOSIS_API_KEY": "FROMFILE"}), encoding="utf-8")
    assert resolve_api_key(None) == "FROMENV"


def test_missing_everywhere_raises(monkeypatch, tmp_path):
    monkeypatch.delenv("KOSIS_API_KEY", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))  # no credentials file
    with pytest.raises(KOSISConfigError):
        resolve_api_key(None)


def test_malformed_file_raises(monkeypatch, tmp_path):
    monkeypatch.delenv("KOSIS_API_KEY", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config_dir = tmp_path / "pykosis"
    config_dir.mkdir()
    (config_dir / "credentials.json").write_text("not json", encoding="utf-8")
    with pytest.raises(KOSISConfigError):
        resolve_api_key(None)
