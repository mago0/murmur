# dictation

Hotkey-triggered voice dictation for Wayland. Records audio via pw-record,
transcribes with GPU-accelerated faster-whisper, and copies the result to the
clipboard.

## Architecture

Three components work together:

```
dictate-toggle.sh  (hotkey script)
        |
        | Unix socket (start/stop commands)
        v
dictation-daemon   (long-running service)
        |
        | pw-record -> WAV -> faster-whisper
        v
   transcription -> wl-copy -> clipboard
        |
        v
   history.log (~/.local/share/dictation/history.log)
```

- **dictate-toggle.sh** - Shell script bound to a hotkey. Sends `start` or
  `stop` commands to the daemon via a Unix socket.
- **dictation-daemon** - Systemd user service. Manages recording and
  transcription. Keeps the Whisper model loaded in GPU memory between uses.
- **dictation-client** - CLI utility for sending commands to the daemon and
  querying its status.

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
| `DICTATION_MODEL` | `base.en` | Whisper model name (e.g. `tiny.en`, `small.en`, `medium.en`) |
| `DICTATION_DEVICE` | `cuda` | Inference device (`cuda` or `cpu`) |
| `DICTATION_COMPUTE_TYPE` | `float16` | Compute type (`float16`, `int8_float16`, `int8`) |
| `DICTATION_AUDIO_SOURCE` | *(default PipeWire source)* | PipeWire source name for pw-record |
| `DICTATION_SOCKET` | `$XDG_RUNTIME_DIR/dictation.sock` | Unix socket path |
| `DICTATION_LOG` | `$XDG_DATA_HOME/dictation/history.log` | Path for transcription history log |
| `DICTATION_TMPDIR` | `$XDG_RUNTIME_DIR` | Directory for temporary WAV files |

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
