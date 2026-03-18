# murmur

Hotkey-triggered voice dictation for Wayland. Records audio via pw-record,
transcribes with GPU-accelerated faster-whisper, and copies the result to the
clipboard.

## Architecture

Three components work together:

```
[Niri keybinding: Mod+D]
        |
        v
murmur-toggle.sh    -- PID file toggle for pw-record
        |
        | (on stop recording)
        v
murmur-client     -- sends "transcribe <path>" over Unix socket
        |
        v
murmur-daemon     -- faster-whisper model warm in VRAM, transcribes,
                        copies to clipboard, logs, notifies
```

- **murmur-toggle.sh** - Shell script bound to a hotkey. Manages pw-record
  directly (start/stop via PID file). On stop, sends the audio to the daemon
  for transcription via murmur-client.
- **murmur-daemon** - Systemd user service. Keeps the Whisper model loaded
  in GPU memory and handles transcription, clipboard copy, logging, and
  notifications.
- **murmur-client** - Thin CLI for sending commands to the daemon over the
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
git clone https://github.com/yourusername/murmur.git
cd murmur
./install.sh
```

The install script creates a Python virtual environment, installs dependencies,
installs the systemd user service, and copies the toggle script to
`~/.local/bin/`.

## Configuration

All configuration is done via environment variables. Set them in
`~/.config/systemd/user/murmur.service.d/override.conf` using
`systemctl --user edit murmur`.

| Variable | Default | Description |
|---|---|---|
| `MURMUR_MODEL` | `small.en` | Whisper model name (e.g. `tiny.en`, `base.en`, `medium.en`) |
| `MURMUR_DEVICE` | `cuda` | Inference device (`cuda` or `cpu`) |
| `MURMUR_COMPUTE_TYPE` | `float16` | Compute type (`float16`, `int8_float16`, `int8`) |
| `MURMUR_AUDIO_SOURCE` | *(default PipeWire source)* | PipeWire source name for pw-record |
| `MURMUR_SOCKET` | `/run/user/$UID/murmur.sock` | Unix socket path |
| `MURMUR_LOG` | `~/.local/share/murmur/history.log` | Path for transcription history log |
| `MURMUR_TMPDIR` | `/tmp` | Directory for temporary WAV files and PID file |

## Niri Keybinding

Add to `~/.config/niri/config.kdl`:

```kdl
binds {
    Mod+D { spawn "murmur-toggle.sh"; }
}
```

## Usage

1. Start the daemon (enabled automatically by the installer):
   ```bash
   systemctl --user start murmur
   ```

2. Press `Mod+D` to begin recording. A notification will appear.

3. Press `Mod+D` again to stop recording and transcribe. The transcribed
   text is copied to the clipboard automatically.

4. Paste as normal (`Ctrl+V` or middle-click).

Transcriptions are appended to the history log at
`~/.local/share/murmur/history.log`.

## Troubleshooting

View live daemon logs:

```bash
journalctl --user -u murmur -f
```

Check daemon status:

```bash
murmur-client status
```

Restart the daemon:

```bash
systemctl --user restart murmur
```

If the model download fails on first run, check that you have internet access
and sufficient disk space in `~/.cache/huggingface/`.

## License

MIT. See [LICENSE](LICENSE).
