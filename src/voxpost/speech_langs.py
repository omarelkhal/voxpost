"""Speech-check input fixture languages and Supertonic TTS output languages."""

from __future__ import annotations

# Supertonic 3 speakable / TTS output codes (must match local TTS support).
SUPERTONIC_OUTPUT_LANGS: frozenset[str] = frozenset(
    {
        "ar",
        "bg",
        "hr",
        "cs",
        "da",
        "nl",
        "en",
        "et",
        "fi",
        "fr",
        "de",
        "el",
        "hi",
        "hu",
        "id",
        "it",
        "ja",
        "ko",
        "lv",
        "lt",
        "pl",
        "pt",
        "ro",
        "ru",
        "sk",
        "sl",
        "es",
        "sv",
        "tr",
        "uk",
        "vi",
    }
)

SUPERTONIC_OUTPUT_LANGS_SORTED: tuple[str, ...] = tuple(sorted(SUPERTONIC_OUTPUT_LANGS))


def validate_output_lang(code: str) -> str:
    """Return normalized output language code or raise ValueError."""
    normalized = code.strip().lower()
    if normalized not in SUPERTONIC_OUTPUT_LANGS:
        allowed = ", ".join(SUPERTONIC_OUTPUT_LANGS_SORTED)
        raise ValueError(
            f"Unsupported output language {code!r}. "
            f"Choose a Supertonic TTS code: {allowed}"
        )
    return normalized


def infer_fixture_input_lang(case_id: str, explicit: str | None = None) -> str:
    """Derive fixture input language from JSON field or ``case_id`` prefix."""
    if explicit and explicit.strip():
        return explicit.strip().lower()
    prefix = case_id.split("_", 1)[0].lower()
    if len(prefix) == 2 and prefix.isalpha():
        return prefix
    return "unknown"


def describe_input_langs(cases: tuple[object, ...]) -> str:
    """
    Leaderboard / report label for which email languages were exercised.

    Single-language filter → ``en``, ``fr``, etc. Multiple → ``multi``.
    """
    langs = sorted({getattr(c, "input_lang", "unknown") for c in cases})
    if len(langs) == 1:
        return langs[0]
    return "multi"
