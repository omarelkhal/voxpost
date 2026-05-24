## Learned User Preferences

- Prefer a building-blocks approach: perfect Gmail event detection (Block 1) before summarization or TTS.
- No mail storage — event-driven pipeline: detect → process in memory → speak → discard.
- End users must not run gcloud or GCP setup; only OAuth "Connect Gmail".
- Want local on-device TTS, not cloud TTS APIs.
- Summarization must be 100% on-device after model download — no third-party or cloud inference APIs (trust/privacy product requirement).
- Length-adaptive speakable lines: brief for short mail, descriptive multi-sentence for long mail — no artificial word cap; trust summarizer over vague intent fallbacks on long bodies.
- Attachment content not fed to summarizer until desktop UI opt-in; v1 only attachment metadata awareness.
- Filter noise (newsletters); silence is a feature — **Block 2 rules deferred until desktop UI (Block 5)**; no headless rules config for now.
- Care about speakable-line and TTS quality — intent-first assistant briefings (not neutral summaries); spoken language from TOML only (`[speech].target_lang` when fixed, else `[tts].lang`), never the email language; expand abbreviations, spell clock times, strip forwarded noise, reject @ symbols and vague sender phrasing; firm spam template only for real marketing mail, hedge misapplied spam on important mail.
- Block 3 is not done until manual `speech-check` passes on the full fixture set (24 diverse cases); `--auto-grade` is CI-only — do not overfit gates or prompts to a small subset.
- Prefer structured chat-LM input (sender, forward flag, attachment metadata) computed in Python before inference — not ambiguous plain From/Body alone.
- Local listen daily driver is Qwen/Qwen3.5-0.8B; Qwen3.5-2B pegs CPU on typical machines — use 2B only via HF `prompt-check` oracle, not on-device listen.

## Learned Workspace Facts

- Voxpost is a local Gmail TTS companion desktop app.
- Block 1 uses Gmail watch + Pub/Sub + history.list for new-mail events; Block 1b adds attachment metadata (`has_attachments`, `attachments: []`) with no attachment bytes downloaded.
- Block 3 local summarizer → `speakable_line` via `_SPEAKABLE_CONTRACT_CORE` (spam rubric, always-IMPORTANT list, five in-system few-shots, banned phrases); seq2seq (mT5 XLSum, FLAN, T5Gemma2) and chat-LM (Qwen/SmolLM/Phi); shipped default mT5 XLSum — no instruction prefix on XLSum; T5Gemma2 HF-gated; local daily driver **Qwen/Qwen3.5-0.8B** (~5/24 speech-check); **Qwen/Qwen3.5-2B** HF prompt-check oracle ~23/24 — too CPU-heavy for local listen on CPU-only setups.
- Block 3 QA: `voxpost summarize speech-check [--model] [--workers]` — 24 diverse fixtures, manual review default; `--auto-grade` for CI heuristics only; `resource-check` for per-case RAM/CPU; `--compare-formats` for plain vs structured JSON input; `prompt-check` runs HF Inference prompt oracle (dev only, not listen) — Qwen3.5-2B requires `--provider featherless-ai`.
- Chat-LM structured input via `summarizer_context.py` (`original_sender`, `is_forward`, attachments); `[summarize] chat_input_format` = `plain` or `structured`.
- Speakable quality path: `speakable_gate.py` overlap gate + `adjust_misapplied_spam_template` (briefing-first lines with soft spam hedge only — never firm "this looks like spam") + `speakable_polish.py` (times, abbreviations); entity fallbacks (OTP, rejection) always; vague `_intent_hint` only when body ≤60 words; long mail (>120 words) keeps summarizer output when soft gate fails.
- Summarizer runtime in `~/.config/voxpost/voxpost.toml`: `[summarize]` `model` (daily driver `Qwen/Qwen3.5-0.8B`), `device=auto` (CUDA→MPS→CPU), idle unload 10 min, CPU threads 0 = half cores, `chat_max_new_tokens=96` (scales to 128 for long bodies), `load_dtype=auto`; `[speech]` `mode=fixed` (default), `target_lang`; `resolved_speakable_lang()` reads TOML only — never infers from email body.
- Qwen3.5-0.8B warm `listen --summarize`: ~2.1 GB RSS after first mail until idle unload (≥10 min) or listen stops.
- Known Block 3 gap: forwarded mail often has wrong outer Gmail `From:` — use body/header extraction (`extract_forwarded_sender`) for the real sender.
- Block 4 TTS: Supertonic 3 (ONNX); `[tts]` has `model`, `device` (`auto`/CPU/CUDA via onnxruntime-gpu), chime settings; `speak_with_chime` (chime → pause → speakable_line); CLI `voxpost tts download|test`, `voxpost listen --speak`.
- Python 3.11+ daemon; CLI: `voxpost connect`, `listen`, `setup-gcp`, `summarize`, `tts`; `listen --summarize` / `--speak` for live Gmail end-to-end dev testing (no desktop UI); `setup-gcp` / gcloud is operator/dev one-time setup, not the end-user flow.
- Only persistent state: OAuth refresh token + lastHistoryId (no mail archive); v1 Gmail-only; Block 2 + Block 5 UI deferred — pipeline order 1 → 3 → 4 → 5+2 — see `docs/TODO.md`.
