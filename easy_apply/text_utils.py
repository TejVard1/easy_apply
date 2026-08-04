from __future__ import annotations

import re
from collections import Counter

from .config import COMMON_SKILLS, STOPWORDS


EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}")
PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}")
WORD_REGEX = re.compile(r"[a-zA-Z][a-zA-Z0-9+.#/-]{1,}")


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item.strip())
    return result


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_email(text: str) -> str:
    match = EMAIL_REGEX.search(text)
    return match.group(0) if match else ""


def extract_phone(text: str) -> str:
    match = PHONE_REGEX.search(text)
    return match.group(0) if match else ""


def extract_skill_matches(text: str) -> list[str]:
    lower_text = text.lower()
    found = [skill for skill in COMMON_SKILLS if skill in lower_text]
    return sorted(dedupe(found), key=str.lower)


def top_keywords(text: str, limit: int = 40) -> list[str]:
    words = [w.lower() for w in WORD_REGEX.findall(text)]
    filtered = [w for w in words if w not in STOPWORDS and len(w) > 2 and not w.isdigit()]
    counts = Counter(filtered)

    ranked = [word for word, _ in counts.most_common(limit * 2)]
    merged_skills = extract_skill_matches(text)

    # Keep skill phrases first, then frequent unigrams.
    output = merged_skills + [w for w in ranked if w not in merged_skills]
    return dedupe(output)[:limit]


def split_bullets(text: str) -> list[str]:
    lines = [line.strip(" -\t") for line in text.splitlines()]
    return [line for line in lines if line]


def lines_after_heading(text: str, heading_pattern: str, max_lines: int = 8) -> list[str]:
    lines = text.splitlines()
    output: list[str] = []
    start_idx: int | None = None

    pattern = re.compile(heading_pattern, re.IGNORECASE)
    for idx, line in enumerate(lines):
        if pattern.search(line):
            start_idx = idx + 1
            break

    if start_idx is None:
        return output

    for line in lines[start_idx : start_idx + max_lines]:
        line = line.strip()
        if not line:
            continue
        if line.endswith(":"):
            break
        output.append(line.lstrip("- ").strip())

    return output
