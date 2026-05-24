"""Expand abbreviations and symbols so speakable lines sound natural in TTS."""

from __future__ import annotations

import os
import re

# French day abbreviations (common in calendar invites: "JEU 14h", "lun. 9h").
_FR_DAYS = {
    "lun": "lundi",
    "mar": "mardi",
    "mer": "mercredi",
    "jeu": "jeudi",
    "ven": "vendredi",
    "sam": "samedi",
    "dim": "dimanche",
}

# English day abbreviations.
_EN_DAYS = {
    "mon": "Monday",
    "tue": "Tuesday",
    "tues": "Tuesday",
    "wed": "Wednesday",
    "thu": "Thursday",
    "thur": "Thursday",
    "thurs": "Thursday",
    "fri": "Friday",
    "sat": "Saturday",
    "sun": "Sunday",
}

# Email / chat shorthand the summarizer may echo in brief lines.
_EMAIL_SHORTHAND = {
    "tmrw": "tomorrow",
    "tom": "tomorrow",
    "tod": "today",
    "mtg": "meeting",
    "appt": "appointment",
    "pls": "please",
    "plz": "please",
    "thx": "thanks",
    "ty": "thank you",
    "asap": "as soon as possible",
    "fyi": "for your information",
    "lmk": "let me know",
    "rsvp": "please reply",
    "approx": "approximately",
    "dept": "department",
    "mgmt": "management",
    "info": "information",
    "msg": "message",
    "doc": "document",
    "docs": "documents",
    "w/": "with",
    "b/c": "because",
    "bc": "because",
}

# Month abbreviations when used as standalone tokens.
_EN_MONTHS = {
    "jan": "January",
    "feb": "February",
    "apr": "April",
    "may": "May",
    "jun": "June",
    "jul": "July",
    "aug": "August",
    "sep": "September",
    "sept": "September",
    "oct": "October",
    "nov": "November",
    "dec": "December",
}

# European 24h shorthand (14h, 18h30) and clock times — not date ordinals like 18th.
_TIME_24H = re.compile(
    r"(?<![\d:/.])(?P<hour>[01]?\d|2[0-3])\s*h(?:\s*(?P<min>[0-5]\d))?(?![a-zA-Z])",
    re.IGNORECASE,
)
_TIME_24H_COLON = re.compile(r"\b(?P<hour>[01]?\d|2[0-3]):(?P<min>[0-5]\d)\b")
_TIME_12H = re.compile(
    r"\b(?P<hour>1[0-2]|0?[1-9])(?::(?P<min>[0-5]\d))?\s*(?P<ampm>a\.?\s*m\.?|p\.?\s*m\.?)\b",
    re.IGNORECASE,
)


def speakable_lang() -> str:
    """
    Locale hint for abbreviation expansion.

    ``en`` (default), ``fr``, or ``all`` (apply English and French tables).
    Override with ``VOXPOST_SPEAKABLE_LANG``.
    """
    raw = os.environ.get("VOXPOST_SPEAKABLE_LANG", "all").strip().lower()
    if raw in {"en", "fr", "all"}:
        return raw
    return "all"


def _replace_token(text: str, token: str, replacement: str) -> str:
    pattern = rf"\b{re.escape(token)}\.?\b"
    return re.sub(pattern, replacement, text, flags=re.IGNORECASE)


def _replace_all_caps_token(text: str, token: str, replacement: str) -> str:
    """Expand tokens like ``JEU`` without touching lowercase homographs (e.g. French ``jeu`` = game)."""
    pattern = rf"\b{re.escape(token.upper())}\.?\b"
    return re.sub(pattern, replacement, text)


def _apply_table(text: str, table: dict[str, str], *, all_caps_only: bool = False) -> str:
    for token, replacement in table.items():
        if all_caps_only:
            text = _replace_all_caps_token(text, token, replacement)
        else:
            text = _replace_token(text, token, replacement)
    return text


def _polish_email_addresses(text: str) -> str:
    """Replace address literals so TTS does not read at-signs and domains aloud."""

    def repl(match: re.Match[str]) -> str:
        local = match.group(1).replace(".", " ")
        domain = match.group(2).split(".")[0]
        return f"{local} at {domain}"

    return re.sub(r"\b([\w.+-]+)@([\w.-]+\.\w+)\b", repl, text)


def _spell_minute_en(minute: int) -> str:
    from voxpost.speakable_numbers import spell_cardinal

    if minute == 0:
        return ""
    if minute < 10:
        return f"oh {spell_cardinal(minute, lang='en')}"
    return spell_cardinal(minute, lang="en")


def _spell_time_en(hour24: int, minute: int = 0) -> str:
    from voxpost.speakable_numbers import spell_cardinal

    if hour24 == 0 and minute == 0:
        return "midnight"
    if hour24 == 12 and minute == 0:
        return "noon"

    if hour24 == 0:
        hour12, period = 12, "a.m."
    elif hour24 < 12:
        hour12, period = hour24, "a.m."
    elif hour24 == 12:
        hour12, period = 12, "p.m."
    else:
        hour12, period = hour24 - 12, "p.m."

    hour_word = spell_cardinal(hour12, lang="en")
    min_part = _spell_minute_en(minute)
    if min_part:
        return f"{hour_word} {min_part} {period}"
    return f"{hour_word} {period}"


def _spell_time_fr(hour24: int, minute: int = 0) -> str:
    _FR_HOUR = (
        "zéro",
        "une",
        "deux",
        "trois",
        "quatre",
        "cinq",
        "six",
        "sept",
        "huit",
        "neuf",
        "dix",
        "onze",
        "douze",
        "treize",
        "quatorze",
        "quinze",
        "seize",
        "dix-sept",
        "dix-huit",
        "dix-neuf",
        "vingt",
        "vingt et une",
        "vingt-deux",
        "vingt-trois",
    )
    hour_word = _FR_HOUR[hour24]
    if minute == 0:
        heure = "heure" if hour24 == 1 else "heures"
        return f"{hour_word} {heure}"
    from voxpost.speakable_numbers import spell_cardinal

    min_word = spell_cardinal(minute, lang="en")
    return f"{hour_word} heures {min_word}"


def _replace_time_match(match: re.Match[str], *, lang: str) -> str:
    hour = int(match.group("hour"))
    minute = int(match.group("min") or 0)
    if lang.startswith("fr"):
        return _spell_time_fr(hour, minute)
    return _spell_time_en(hour, minute)


def _replace_12h_match(match: re.Match[str], *, lang: str) -> str:
    if lang.startswith("fr"):
        # Already has am/pm — leave for fr or normalize later.
        return match.group(0)
    hour = int(match.group("hour"))
    minute = int(match.group("min") or 0)
    ampm = match.group("ampm").lower().replace(" ", "").replace(".", "")
    period = "a.m." if ampm.startswith("a") else "p.m."
    from voxpost.speakable_numbers import spell_cardinal

    hour_word = spell_cardinal(hour, lang="en")
    min_part = _spell_minute_en(minute)
    if min_part:
        return f"{hour_word} {min_part} {period}"
    return f"{hour_word} {period}"


def _polish_times(text: str, *, lang: str = "en") -> str:
    """Turn clock shorthand (18h, 14:30, 6pm) into spoken time phrases."""
    if not text:
        return text

    def repl_24h(match: re.Match[str]) -> str:
        return _replace_time_match(match, lang=lang)

    def repl_colon(match: re.Match[str]) -> str:
        return _replace_time_match(match, lang=lang)

    def repl_12h(match: re.Match[str]) -> str:
        return _replace_12h_match(match, lang=lang)

    text = _TIME_24H.sub(repl_24h, text)
    text = _TIME_24H_COLON.sub(repl_colon, text)
    if lang.startswith("en"):
        text = _TIME_12H.sub(repl_12h, text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _polish_symbols(text: str) -> str:
    text = _polish_email_addresses(text)
    text = text.replace("&", " and ")
    text = re.sub(r"(\d)\s*%", r"\1 percent", text)
    text = re.sub(r"\be\.g\.\b", "for example", text, flags=re.IGNORECASE)
    text = re.sub(r"\bi\.e\.\b", "that is", text, flags=re.IGNORECASE)
    text = re.sub(r"\betc\.\b", "and so on", text, flags=re.IGNORECASE)
    text = re.sub(r"\bvs\.\b", "versus", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def polish_for_tts(text: str, *, lang: str | None = None) -> str:
    """
    Make a summary line easier for TTS: spell out days, months, shorthand, numbers.
    """
    if not text or not text.strip():
        return text

    locale = lang or speakable_lang()
    polished = text.strip()

    # French day codes first (MAR/JEU…) before English month/day tables run case-insensitive.
    if locale in {"fr", "all"}:
        polished = _apply_table(polished, _FR_DAYS, all_caps_only=True)

    if locale in {"en", "all"}:
        polished = _apply_table(polished, _EN_DAYS)
        polished = _apply_table(polished, _EN_MONTHS)
        polished = _apply_table(polished, _EMAIL_SHORTHAND)

    time_lang = locale if locale in {"en", "fr"} else "en"
    polished = _polish_times(polished, lang=time_lang)

    polished = _polish_symbols(polished)

    if locale in {"en", "fr"}:
        from voxpost.speakable_numbers import polish_numbers_for_tts

        polished = polish_numbers_for_tts(polished, lang=locale)

    return polished


def polish_email_text(text: str, *, lang: str | None = None) -> str:
    """Normalize subject/body before summarization so the model sees full words."""
    if not text or not text.strip():
        return text
    return polish_for_tts(text, lang=lang)
