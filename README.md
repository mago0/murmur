# dictation

Hotkey-triggered voice dictation for Wayland. Records audio via pw-record,
transcribes with GPU-accelerated faster-whisper, and copies the result to the
clipboard.

## Architecture

Three components work together:

```
[Niri keybinding: Mod+Shift+D]
        |
        v
dictate-toggle.sh    -- PID file toggle for pw-record
        |
        | (on stop recording)
        v
dictation-client     -- sends "transcribe <path>" over Unix socket
        |
        v
dictation-daemon     -- faster-whisper model warm in VRAM, transcribes,
                        copies to clipboard, logs, notifies
```

- **dictate-toggle.sh** - Shell script bound to a hotkey. Manages pw-record
  directly (start/stop via PID file). On stop, sends the audio to the daemon
  for transcription via dictation-client.
- **dictation-daemon** - Systemd user service. Keeps the Whisper model loaded
  in GPU memory and handles transcription, clipboard copy, logging, and
  notifications.
- **dictation-client** - Thin CLI for sending commands to the daemon over the
  Unix socket.

## Prerequisites

- NVIDIA GPU with CUDA (required for GPU-accelerated transcription)
- PipeWire >= 0.3.44
- Wayland compositor (tested with Niri)
- Python >= 3.11

System packages:

```
wl-clipboard
libnotify-bin
pipewire-audio (or equivalent, providing pw-record)
```

## Installation

```bash
git clone https://github.com/yourusername/dictation.git
cd dictation
./install.sh
```

The install script creates a Python virtual environment, installs dependencies,
installs the systemd user service, and copies the toggle script to
`~/.local/bin/`.

## Configuration

All configuration is done via environment variables. Set them in
`~/.config/systemd/user/dictation.service.d/override.conf` using
`systemctl --user edit dictation`.

| Variable | Default | Description |
|---|---|---|
| `DICTATION_MODEL` | `small.en` | Whisper model name (e.g. `tiny.en`, `base.en`, `medium.en`) |
| `DICTATION_DEVICE` | `cuda` | Inference device (`cuda` or `cpu`) |
| `DICTATION_COMPUTE_TYPE` | `float16` | Compute type (`float16`, `int8_float16`, `int8`) |
| `DICTATION_AUDIO_SOURCE` | *(default PipeWire source)* | PipeWire source name for pw-record |
| `DICTATION_SOCKET` | `/run/user/$UID/dictation.sock` | Unix socket path |
| `DICTATION_LOG` | `~/.local/share/dictation/history.log` | Path for transcription history log |
| `DICTATION_TMPDIR` | `/tmp` | Directory for temporary WAV files and PID file |

## Niri Keybinding

Add to `~/.config/niri/config.kdl`:

```kdl
binds {
    Mod+Shift+D { spawn "dictate-toggle.sh"; }
}
```

## Usage

1. Start the daemon (enabled automatically by the installer):
   ```bash
   systemctl --user start dictation
   ```

2. Press `Mod+Shift+D` to begin recording. A notification will appear.

3. Press `Mod+Shift+D` again to stop recording and transcribe. The transcribed
   text is copied to the clipboard automatically.

4. Paste as normal (`Ctrl+V` or middle-click).

Transcriptions are appended to the history log at
`~/.local/share/dictation/history.log`.

## Troubleshooting

View live daemon logs:

```bash
journalctl --user -u dictation -f
```

Check daemon status:

```bash
dictation-client status
```

Restart the daemon:

```bash
systemctl --user restart dictation
```

If the model download fails on first run, check that you have internet access
and sufficient disk space in `~/.cache/huggingface/`.

## License

MIT. See [LICENSE](LICENSE).
