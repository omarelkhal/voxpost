# Block 4 — Local TTS (Supertonic 3)

Block 4 turns a **`speakable_line`** from Block 3 into **local audio playback**. Everything stays on-device; no cloud TTS API.

## Engine

- **[Supertonic 3](https://github.com/supertone-inc/supertonic)** — ONNX Runtime, `pip install supertonic`
- Defaults if no config file: **`M1`**, **`en`**, steps **8**, speed **1.05**
- Models auto-download on first use; explicit download via CLI

## Configuration (`voxpost.toml`)

Copy the example file into your config directory:

```bash
mkdir -p ~/.config/voxpost
cp voxpost.toml.example ~/.config/voxpost/voxpost.toml
```

`voxpost listen --speak`, `voxpost tts test`, and `voxpost tts warmup` read **`~/.config/voxpost/voxpost.toml`** when present. Missing file → built-in defaults.

```toml
[tts]
voice = "M1"
lang = "en"          # or fr, de, na, … (Supertonic language codes)
total_steps = 8
speed = 1.05
playback = "auto"    # auto | sounddevice | aplay
auto_download = true
chime_before_speak = true   # notification chime before speech
chime_pause_ms = 350        # gap after chime (ms)
# chime_file = "/path/to/custom.wav"

[speech]
mode = "auto"        # reserved — language mode wired in a later block
target_lang = "fr"
```

Environment variables override TOML (useful for dev):

| Variable | `[tts]` field |
|----------|----------------|
| `VOXPOST_TTS_VOICE` | `voice` |
| `VOXPOST_TTS_LANG` | `lang` |
| `VOXPOST_TTS_TOTAL_STEPS` | `total_steps` |
| `VOXPOST_TTS_SPEED` | `speed` |
| `VOXPOST_TTS_PLAYBACK` | `playback` |
| `VOXPOST_TTS_AUTO_DOWNLOAD` | `auto_download` |
| `VOXPOST_TTS_CHIME` | `chime_before_speak` |
| `VOXPOST_TTS_CHIME_PAUSE_MS` | `chime_pause_ms` |
| `VOXPOST_TTS_CHIME_FILE` | `chime_file` |
| `VOXPOST_SPEECH_LANG_MODE` | `speech.mode` |
| `VOXPOST_SPEECH_TARGET_LANG` | `speech.target_lang` |

## Install

```bash
pip install -e ".[tts]"
voxpost tts download   # optional: prefetch ONNX assets
```

Playback prefers **sounddevice** (PortAudio). On Linux without PortAudio, **aplay** (ALSA) is used as a fallback.

## Test

```bash
voxpost tts test "Voxpost is ready."
voxpost tts warmup    # load model without speaking
```

## Listen with speech

```bash
pip install -e ".[summarize,tts]"
voxpost summarize download
voxpost tts download

voxpost listen --speak
```

Each new inbox message:

1. Summarizes locally (Block 3)
2. Prints **SummarizedMailEvent JSON** to stdout
3. Plays a short **notification chime** (on by default), pauses briefly (~350 ms), then plays the synthesized line

The chime runs **after** speech is synthesized so model load time does not sit between the ping and your voice line. With `--speak`, the listener also **warms up** the TTS model in the background at startup.

`--speak` implies `--summarize` (TTS needs a speakable line).

## Privacy

- Supertonic ONNX weights download once from Hugging Face; inference is local only
- Spoken text is the same ephemeral **`speakable_line`** — not stored on disk
- No email content sent to a cloud TTS vendor

## Pipeline

```text
NewMailEvent → EmailSummarizer → speakable_line → synthesize → chime → play audio → discard
```

TTS failures are **non-fatal**: the listener logs the error and keeps processing Gmail events.

## Future UI (Block 5)

The desktop app edits **`~/.config/voxpost/voxpost.toml`** (same file the daemon reads). Map UI controls to TOML sections:

| UI control | Config |
|------------|--------|
| Listen on/off | start/stop `voxpost listen` |
| Speak on/off | listen flag or `[listen] speak = true` (TBD) |
| Voice / speed / steps / lang | `[tts]` → Supertonic `SupertonicSpeaker` |
| Language mode | `[speech]` → summarize + TTS lang per message |
| Output device | `[tts].playback` |
| VIP / quiet hours | `[rules]` (Block 2) |

Block 2 rules (VIP, quiet hours, keywords) will gate whether an event reaches summarize/TTS once the settings UI ships.

## Module

- `src/voxpost/tts.py` — `SupertonicSpeaker`, playback helpers, download/warmup
