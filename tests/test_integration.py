import os
import socket
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from murmur.daemon import MurmurDaemon
from murmur.client import send_command


@pytest.fixture
def integration_env(tmp_path):
    """Spin up a daemon with mocked transcriber and return paths."""
    sock_path = str(tmp_path / "murmur.sock")
    log_path = str(tmp_path / "history.log")

    with patch("murmur.daemon.Transcriber") as mock_cls:
        mock_transcriber = MagicMock()
        mock_transcriber.transcribe.return_value = "the quick brown fox"
        mock_cls.return_value = mock_transcriber

        daemon = MurmurDaemon(
            model="base.en",
            device="cpu",
            compute_type="int8",
            socket_path=sock_path,
            log_path=log_path,
        )

        t = threading.Thread(target=daemon.run, daemon=True)
        t.start()
        # Wait for daemon to be ready
        time.sleep(0.2)

        yield {
            "sock_path": sock_path,
            "log_path": log_path,
            "daemon": daemon,
            "tmp_path": tmp_path,
            "mock_transcriber": mock_transcriber,
        }

        daemon.shutdown()
        t.join(timeout=3)


@patch("murmur.daemon.subprocess.run")
def test_full_transcription_flow(mock_run, integration_env):
    """Client sends transcribe, daemon processes, result appears in log."""
    env = integration_env
    audio = env["tmp_path"] / "test.wav"
    audio.write_bytes(b"\x00" * 2000)

    resp = send_command(env["sock_path"], f"transcribe {audio}", timeout=5.0)

    assert resp == "OK the quick brown fox"
    assert os.path.exists(env["log_path"])
    with open(env["log_path"]) as f:
        content = f.read()
    assert "the quick brown fox" in content


def test_status_while_idle(integration_env):
    """Status returns ready when daemon is idle."""
    resp = send_command(integration_env["sock_path"], "status", timeout=2.0)
    assert resp == "ready"


@patch("murmur.daemon.subprocess.run")
def test_multiple_transcriptions(mock_run, integration_env):
    """Multiple transcriptions append to the same log."""
    env = integration_env

    for i in range(3):
        audio = env["tmp_path"] / f"test{i}.wav"
        audio.write_bytes(b"\x00" * 2000)
        send_command(env["sock_path"], f"transcribe {audio}", timeout=5.0)

    with open(env["log_path"]) as f:
        lines = f.readlines()
    assert len(lines) == 3
