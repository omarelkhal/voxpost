"""Spell numbers for TTS: digit-by-digit codes, money, cardinals."""

from __future__ import annotations

import re

_DIGIT_EN = (
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
)
_DIGIT_FR = (
    "zéro",
    "un",
    "deux",
    "trois",
    "quatre",
    "cinq",
    "six",
    "sept",
    "huit",
    "neuf",
)

_CODE_CONTEXT = re.compile(
    r"(?:verification\s+code|security\s+code|auth(?:entication)?\s+code|"
    r"one[- ]time|otp|pin\b|2fa|passcode|"
    r"code\s+de\s+(?:v[ée]rification|confirmation)|"
    r"votre\s+code|your\s+code|enter\s+(?:the\s+)?code|"
    r"confirm(?:ation)?\s+code|confirmation\s+code|"
    r"\d+\s+chiffres|à\s+\d+\s+chiffres)",
    re.IGNORECASE,
)

_MONEY_CONTEXT = re.compile(
    r"(?:[$€£]|usd|eur|gbp|\bdollars?\b|\beuros?\b|\bcents?\b|payment|invoice|total|amount|"
    r"price|paid|refund|fee|salary|bonus)",
    re.IGNORECASE,
)

_NUMBER_RE = re.compile(
    r"(?<![\w.])(?P<prefix>[$€£]\s*)?"
    r"(?P<num>(?:\d{1,3}(?:[,\s]\d{3})+|\d+)(?:[.,]\d{1,2})?)"
    r"(?P<suffix>\s*(?:usd|eur|gbp|dollars?|euros?|cents?))?"
    r"(?!\w)",
    re.IGNORECASE,
)


def spell_digits(value: str, *, lang: str = "en") -> str:
    """Spell each digit separately (311164 → three one one one six four)."""
    table = _DIGIT_FR if lang.startswith("fr") else _DIGIT_EN
    parts: list[str] = []
    for ch in value:
        if ch.isdigit():
            parts.append(table[int(ch)])
    return " ".join(parts)


def _spell_under_thousand_en(n: int) -> str:
    ones = (
        "zero",
        "one",
        "two",
        "three",
        "four",
        "five",
        "six",
        "seven",
        "eight",
        "nine",
        "ten",
        "eleven",
        "twelve",
        "thirteen",
        "fourteen",
        "fifteen",
        "sixteen",
        "seventeen",
        "eighteen",
        "nineteen",
    )
    tens = (
        "",
        "",
        "twenty",
        "thirty",
        "forty",
        "fifty",
        "sixty",
        "seventy",
        "eighty",
        "ninety",
    )
    if n < 20:
        return ones[n]
    if n < 100:
        t, o = divmod(n, 10)
        return tens[t] if o == 0 else f"{tens[t]}-{ones[o]}"
    h, rem = divmod(n, 100)
    head = f"{ones[h]} hundred"
    return head if rem == 0 else f"{head} {_spell_under_thousand_en(rem)}"


def spell_cardinal(n: int, *, lang: str = "en") -> str:
    """Spell a whole number for TTS (English or French stub via digits fallback)."""
    if lang.startswith("fr"):
        # v1: French cardinals beyond small counts are rare in mail; use EN table for now
        # when fr TTS is selected for money we still prefer spelled EN if speech is mixed.
        pass
    if n == 0:
        return "zero"
    if n < 0:
        return f"minus {spell_cardinal(-n, lang=lang)}"

    scales = (
        (1_000_000_000, "billion"),
        (1_000_000, "million"),
        (1_000, "thousand"),
    )
    parts: list[str] = []
    rest = n
    for scale, name in scales:
        if rest >= scale:
            count, rest = divmod(rest, scale)
            chunk = _spell_under_thousand_en(count)
            parts.append(f"{chunk} {name}")
    if rest:
        parts.append(_spell_under_thousand_en(rest))
    return " ".join(parts)


def _parse_amount(num_text: str) -> tuple[int, int] | None:
    """Return (whole, cents) from numeric text."""
    cleaned = num_text.strip().replace(" ", "")
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        if re.search(r",\d{2}$", cleaned):
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    try:
        if "." in cleaned:
            whole_s, frac_s = cleaned.split(".", 1)
            whole = int(whole_s) if whole_s else 0
            frac = int(frac_s.ljust(2, "0")[:2])
            return whole, frac
        return int(cleaned), 0
    except ValueError:
        return None


def _spell_money(match: re.Match[str], *, lang: str) -> str:
    prefix = (match.group("prefix") or "").strip()
    suffix = (match.group("suffix") or "").strip().lower()
    parsed = _parse_amount(match.group("num"))
    if parsed is None:
        return match.group(0)
    whole, cents = parsed

    if prefix == "$" or "dollar" in suffix or suffix == "usd":
        unit = "dollar" if whole == 1 and cents == 0 else "dollars"
    elif prefix == "€" or "euro" in suffix or suffix == "eur":
        unit = "euro" if whole == 1 and cents == 0 else "euros"
    elif prefix == "£" or "gbp" in suffix:
        unit = "pound" if whole == 1 and cents == 0 else "pounds"
    elif "cent" in suffix:
        unit = "cent" if whole == 1 else "cents"
        return f"{spell_cardinal(whole, lang=lang)} {unit}"
    else:
        unit = "dollars"

    spoken = f"{spell_cardinal(whole, lang=lang)} {unit}"
    if cents:
        cent_word = "cent" if cents == 1 else "cents"
        spoken += f" and {spell_cardinal(cents, lang=lang)} {cent_word}"
    return spoken


def _context_window(text: str, start: int, end: int, *, radius: int = 72) -> str:
    lo = max(0, start - radius)
    hi = min(len(text), end + radius)
    return text[lo:hi]


def _number_kind(text: str, start: int, end: int, raw: str) -> str:
    window = _context_window(text, start, end)
    digits_only = re.sub(r"\D", "", raw)
    if not digits_only:
        return "skip"
    if _CODE_CONTEXT.search(window):
        return "code"
    if _MONEY_CONTEXT.search(window) or raw.strip().startswith(("$", "€", "£")):
        return "money"
    if len(digits_only) >= 10:
        return "code"
    if len(digits_only) <= 2:
        return "cardinal"
    if len(digits_only) <= 6:
        return "cardinal"
    return "code"


def polish_numbers_for_tts(text: str, *, lang: str = "en") -> str:
    """Replace digit runs with spoken forms suited for TTS."""
    if not text or not text.strip():
        return text

    out: list[str] = []
    cursor = 0
    for match in _NUMBER_RE.finditer(text):
        start, end = match.span()
        out.append(text[cursor:start])
        raw = match.group(0)
        kind = _number_kind(text, start, end, raw)
        if kind == "skip":
            out.append(raw)
        elif kind == "money":
            out.append(_spell_money(match, lang=lang))
        elif kind == "code":
            digits = re.sub(r"\D", "", match.group("num"))
            out.append(spell_digits(digits, lang=lang))
        else:
            parsed = _parse_amount(match.group("num"))
            if parsed and parsed[1] == 0:
                out.append(spell_cardinal(parsed[0], lang=lang))
            else:
                out.append(_spell_money(match, lang=lang))
        cursor = end
    out.append(text[cursor:])
    return re.sub(r"\s+", " ", "".join(out)).strip()


def extract_verification_code(body: str, subject: str = "") -> str | None:
    """Return a short numeric code when the mail looks like OTP / verification."""
    combined = f"{subject}\n{body}"
    if not _CODE_CONTEXT.search(combined):
        return None
    for match in re.finditer(r"\b(\d{4,8})\b", body):
        return match.group(1)
    return None


def verification_code_line(body: str, subject: str, *, lang: str = "en") -> str | None:
    code = extract_verification_code(body, subject)
    if not code:
        return None
    spoken = spell_digits(code, lang=lang)
    combined = f"{subject}\n{body}".lower()
    cancellation = bool(re.search(r"annulation|cancel(?:lation)?", combined, re.IGNORECASE))
    if lang.startswith("fr"):
        if cancellation:
            return f"Votre code de confirmation d'annulation est {spoken}."
        return f"Votre code de vérification est {spoken}."
    if cancellation:
        return f"Your order cancellation confirmation code is {spoken}."
    return f"Your verification code is {spoken}."
