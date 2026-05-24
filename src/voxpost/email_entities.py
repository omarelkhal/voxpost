"""Extract signatory, company, and role hints from email body and subject."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

_CLOSING = re.compile(
    r"(?:Sincerely|Best regards|Kind regards|Regards|Cordially|Warm regards),?\s*",
    re.IGNORECASE,
)

_BOLD_NAME = re.compile(r"\*([A-Z][^\*\n]{2,60})\*")

_TITLE_HINT = re.compile(
    r"\b(?:Manager|Director|Strategist|Engineer|Recruiter|Consultant|"
    r"Specialist|Coordinator|Lead|Head|Officer|Analyst|Partner|President|CEO|"
    r"Strategist|Associate|Advisor|Representative)\b",
    re.IGNORECASE,
)

_COMPANY_SUFFIX = re.compile(
    r"\b(?:Consulting|Inc\.?|LLC|Ltd\.?|GmbH|Corp\.?|Corporation|Group|Company|"
    r"Partners|Holdings|Technologies|Labs|Studio|Agency)\b",
    re.IGNORECASE,
)

_COMPANY_INTEREST = re.compile(
    r"interest in ([A-Z][\w\s&''.-]{2,80}?" + _COMPANY_SUFFIX.pattern + r")",
    re.IGNORECASE,
)

_SUBJECT_APPLICATION = re.compile(
    r"(?:regarding|about|for)\s+(?:your\s+)?(.+?)\s+application\b",
    re.IGNORECASE,
)

_NAME_LIKE = re.compile(
    r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}$",
)


@dataclass(frozen=True)
class EmailEntities:
    signatory_name: str | None = None
    signatory_title: str | None = None
    company: str | None = None
    application_role: str | None = None


def _strip_subject_prefix(subject: str) -> str:
    text = subject.strip()
    while True:
        match = re.match(r"^(?:Fwd|Fw|Re|Tr|Transféré):\s*", text, re.IGNORECASE)
        if not match:
            break
        text = text[match.end() :].strip()
    return text


def extract_application_role(subject: str | None, body: str) -> str | None:
    if subject:
        clean = _strip_subject_prefix(subject)
        match = _SUBJECT_APPLICATION.search(clean)
        if match:
            role = match.group(1).strip(" .,-")
            if len(role) >= 3:
                return role
    return None


def extract_company(body: str) -> str | None:
    match = _COMPANY_INTEREST.search(body)
    if match:
        return match.group(1).strip()

    lines = [line.strip().strip("*") for line in body.replace("\r", "\n").split("\n") if line.strip()]
    for line in reversed(lines[-10:]):
        if _COMPANY_SUFFIX.search(line) and 4 <= len(line) <= 80:
            if not _NAME_LIKE.match(line):
                return line
    return None


_GREETING_START = frozenset({"bonjour", "hi", "hello", "dear", "thanks", "thank", "cheers"})


def _plausible_signatory(name: str | None) -> bool:
    if not name:
        return False
    parts = name.split()
    if len(parts) > 4:
        return False
    return parts[0].lower() not in _GREETING_START


def _split_name_title(line: str) -> tuple[str | None, str | None]:
    """Parse 'First Last Job Title' on one line."""
    text = line.strip().strip("*")
    if not text:
        return None, None
    words = text.split()
    if len(words) >= 3:
        two = " ".join(words[:2])
        rest = " ".join(words[2:]).strip()
        if _NAME_LIKE.match(two) and _TITLE_HINT.search(rest):
            return two, rest
    for count in range(min(4, len(words)), 1, -1):
        candidate = " ".join(words[:count])
        if not _NAME_LIKE.match(candidate):
            continue
        remainder = " ".join(words[count:]).strip()
        if remainder and _TITLE_HINT.search(remainder):
            return candidate, remainder
        if count >= 2 and not remainder:
            return candidate, None
    return None, None


def extract_signatory(body: str) -> tuple[str | None, str | None]:
    text = body.replace("\r", "\n")
    tail = text[-700:] if len(text) > 700 else text

    bold_matches = list(_BOLD_NAME.finditer(tail))
    if bold_matches:
        name = bold_matches[-1].group(1).strip()
        after = tail[bold_matches[-1].end() :].strip()
        title = None
        if after:
            first_line = after.split("\n")[0].strip()
            if _TITLE_HINT.search(first_line):
                title = first_line
        if _plausible_signatory(name) and len(name.split()) >= 2:
            return name, title

    closing = _CLOSING.search(tail)
    if closing:
        after = tail[closing.end() :].strip()
        lines = [line.strip().strip("*") for line in after.split("\n") if line.strip()]
        if lines:
            if len(lines) == 1 or not _NAME_LIKE.match(lines[0]):
                name, title = _split_name_title(lines[0])
                if _plausible_signatory(name):
                    return name, title
            if _NAME_LIKE.match(lines[0]) and _plausible_signatory(lines[0]):
                title = lines[1] if len(lines) > 1 and _TITLE_HINT.search(lines[1]) else None
                return lines[0], title

    inline = re.search(
        r"(?:Sincerely|Best regards|Kind regards|Regards),?\s*(.+)$",
        tail,
        re.IGNORECASE,
    )
    if inline:
        name, title = _split_name_title(inline.group(1).strip())
        if _plausible_signatory(name):
            return name, title

    lines = [line.strip().strip("*") for line in tail.split("\n") if line.strip()]
    if len(lines) >= 2:
        for index in range(len(lines) - 1, max(len(lines) - 6, 0) - 1, -1):
            line = lines[index]
            if _NAME_LIKE.match(line) and _plausible_signatory(line):
                title = (
                    lines[index + 1]
                    if index + 1 < len(lines) and _TITLE_HINT.search(lines[index + 1])
                    else None
                )
                return line, title
            name, title = _split_name_title(line)
            if _plausible_signatory(name):
                return name, title

    return None, None


def extract_email_entities(body: str, *, subject: str | None = None) -> EmailEntities:
    name, title = extract_signatory(body)
    return EmailEntities(
        signatory_name=name,
        signatory_title=title,
        company=extract_company(body),
        application_role=extract_application_role(subject, body),
    )


def is_application_rejection(body: str) -> bool:
    text = unicodedata.normalize("NFKC", body.lower())
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    text = re.sub(r"\s+", " ", text)
    markers = (
        "move forward with another candidate",
        "not moving forward",
        "decided to move forward with another",
        "will not be moving forward",
        "unfortunately",
        "regret to inform",
        "not selected",
        "other candidates",
    )
    return any(marker in text for marker in markers)
