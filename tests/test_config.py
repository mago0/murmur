import os
import pytest
from dictation.config import get_config


def test_defaults():
    """Config returns sensible defaults when no env vars set."""
    cfg = get_config()
    assert cfg.model == "small.en"
    assert cfg.device == "cuda"
    assert cfg.compute_type == "float16"
    assert cfg.socket_path.endswith("dictation.sock")
    assert cfg.tmpdir == "/tmp"
    assert "history.log" in cfg.log_path


def test_env_override(monkeypatch):
    """Env vars override defaults."""
    monkeypatch.setenv("DICTATION_MODEL", "base.en")
    monkeypatch.setenv("DICTATION_DEVICE", "cpu")
    monkeypatch.setenv("DICTATION_COMPUTE_TYPE", "int8")
    cfg = get_config()
    assert cfg.model == "base.en"
    assert cfg.device == "cpu"
    assert cfg.compute_type == "int8"


def test_socket_path_uses_uid():
    """Socket path includes the current user's UID."""
    cfg = get_config()
    assert f"/run/user/{os.getuid()}/" in cfg.socket_path
