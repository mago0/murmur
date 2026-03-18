# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run tests
.venv/bin/pytest tests/ -v

# Run a single test
.venv/bin/pytest tests/test_daemon.py::test_status_ready -v

# Install for development (creates .venv)
uv venv .venv --python ">=3.11" && uv pip install -e ".[dev]" --python .venv/bin/python

# Install for production use (with CUDA)
./install.sh

# Reinstall after code changes (production venv)
uv pip install ".[cuda]" --python ~/.local/share/murmur/venv/bin/python && systemctl --user restart murmur

# Check daemon status / logs
murmur-client status
journalctl --user -u murmur -f
```

## Architecture

Three-component system connected by a Unix domain socket:

1. **`scripts/murmur-toggle.sh`** - Bash PID-file toggle. On first press, starts `pw-record`. On second press, stops recording and calls `murmur-client transcribe <path>`. Runs from a Niri keybinding - has no access to a login shell, so all defaults are hard-coded with `${VAR:-default}` syntax.

2. **`src/murmur/daemon.py` (`MurmurDaemon`)** - Long-running systemd user service. Loads the faster-whisper model into GPU VRAM at startup, listens on a Unix socket for commands (`transcribe`, `status`, `shutdown`). On transcribe: runs inference, copies result to clipboard via `wl-copy`, appends to history log, sends desktop notification. The `_ensure_cuda_ld_path()` function re-execs the process with correct `LD_LIBRARY_PATH` for NVIDIA pip package libs before any CUDA imports happen.

3. **`src/murmur/client.py`** - Thin socket client. Connects, sends command, reads response. Used by both the toggle script and directly by users.

**`src/murmur/config.py`** - Shared env var config (`MURMUR_*`). All three components use the same variable names and defaults. The bash script duplicates these defaults since it can't import Python.

**`src/murmur/transcribe.py`** - Wraps `faster-whisper`'s `WhisperModel`. Model loaded once at construction, reused across calls. VAD filter enabled with relaxed settings (1000ms silence threshold, 300ms speech padding).

## Key Design Decisions

- The daemon exists to avoid 1-2s model load time on every dictation. VRAM cost is ~1-2GB for `small.en`.
- CUDA libs are bundled via pip (`nvidia-cublas-cu12`, `nvidia-cudnn-cu12`) rather than requiring system CUDA. The daemon re-execs itself to set `LD_LIBRARY_PATH` before the dynamic linker resolves them.
- All config is env vars (`MURMUR_*`), no config files. Systemd overrides via `systemctl --user edit murmur`.
- `pw-record` is stopped with SIGINT (not SIGTERM) so it finalizes the WAV header. The toggle script polls for process exit since `wait` only works for child processes.
