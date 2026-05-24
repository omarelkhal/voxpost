# Speech-check language configuration

Speech-check benchmarks **email input language** (fixture language) separately from **speakable output language** (what TTS will read aloud). Leaderboard rows are only comparable when **model, backend, input filter, and output language** match.

---

## Two language axes

| Axis | CLI flag | Meaning |
|------|----------|---------|
| **Input language** | `--input-lang` | Which fixture emails to run. Filters by each case’s `input_lang` (email body language). Omit or `all` = full multilingual suite (`multi` in reports). |
| **Output language** | `--output-lang` | Language of the **speakable line** the summarizer must produce. Must be a [Supertonic 3](https://github.com/supertonic-ai/supertonic) TTS code. Default: `[speech].target_lang` or `[tts].lang` in `voxpost.toml`. |

**Important:** Output language is **never inferred from the email**. The model is instructed to brief the user in the chosen output language even when the mail is French, Japanese, etc.

---

## Allowed output languages (Supertonic)

`ar`, `bg`, `hr`, `cs`, `da`, `nl`, `en`, `et`, `fi`, `fr`, `de`, `el`, `hi`, `hu`, `id`, `it`, `ja`, `ko`, `lv`, `lt`, `pl`, `pt`, `ro`, `ru`, `sk`, `sl`, `es`, `sv`, `tr`, `uk`, `vi`

List in terminal:

```bash
voxpost summarize speech-check --list-languages
```

---

## Fixture input languages (shipped)

Derived from each JSON fixture’s `input_lang` field, or from the `case_id` prefix (`en_…`, `fr_…`, …):

| Code | Cases (approx.) | Examples |
|------|-----------------|----------|
| `en` | 15 | `en_short_ack`, `en_angry_order` |
| `fr` | 3 | `fr_forward_phone`, `fr_meeting_move` |
| `de` | 1 | `de_tax_notice` |
| `es` | 1 | `es_delivery` |
| `pt` | 1 | `pt_hotel_confirm` |
| `it` | 1 | `it_dinner_invite` |
| `nl` | 1 | `nl_interview_invite` |
| `ja` | 1 | `ja_en_mixed_vendor` (mixed body; tagged `ja`) |

---

## Example commands

Full multilingual suite, English speakable output (default leaderboard shape):

```bash
voxpost summarize speech-check --model qwen3.5:2b
# input=multi, output=en (from TOML if [speech] target_lang = en)
```

English emails only, French speakable output:

```bash
voxpost summarize speech-check --model qwen3.5:2b --input-lang en --output-lang fr
```

French fixtures only, French output:

```bash
voxpost summarize speech-check --model qwen3.5:2b --input-lang fr --output-lang fr
```

---

## TOML vs CLI

| Setting | Source |
|---------|--------|
| Default output language | `~/.config/voxpost/voxpost.toml` → `[speech] mode=fixed` + `target_lang`, else `[tts] lang` |
| Speech-check override | `--output-lang CODE` (benchmark runs should set this explicitly when not `en`) |
| Input filter | `--input-lang CODE` or omit for all fixtures |

---

## Report / run log filename

Auto reports include language tokens:

```text
{model}__{backend}__in-{input}__out-{output}__{completed}of{total}__{status}__run-{id}.md
```

Example:

```text
qwen3.5-2b__ollama__in-multi__out-en__24of24__complete__run-20260524-143052-a1b2c3.md
```

Metadata table inside the file repeats **Input language** and **Output language**.

---

## Leaderboard rows

When opening a PR, include in `docs/MODEL_LEADERBOARD.md`:

- **Input lang** — `multi` (full suite), or `en`, `fr`, … if you filtered
- **Output lang** — Supertonic code used (`en`, `fr`, …)
- **PASS / WEAK / FAIL** — counts for **that** case subset (e.g. 15/24 if `--input-lang en` only)

Do not compare scores across different input/output pairs without noting the mismatch.

---

## Contributing new fixture languages

Use the GitHub issue template **“Multilingual speech-check fixture”** (`.github/ISSUE_TEMPLATE/multilingual_fixture.yml`) or open a PR adding `src/voxpost/speech_check/fixtures/{lang}_{scenario}.json` with:

- `"input_lang": "xx"` (ISO 639-1)
- Realistic `event` (from, subject, body)
- `intent`, `label`, grading hints (`must_mention_any`, `must_not_mention`, `max_words`)

See existing fixtures under `src/voxpost/speech_check/fixtures/`.
