#!/usr/bin/env python3
"""Validate content files against the T120 app's parsing contract.

Checks per unit file:
- frontmatter has every field the app's MarkdownFrontmatterParser requires
- the band directory, score_band_id, and score range agree
- every word line has exactly 6 non-empty-critical fields:
  `- word | meaning | pronunciation | hint | example | translation`
- no duplicate words within a band
- word count per file is a multiple of 10 (chapter size in the app)

Usage: python3 tools/validate_content.py
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content"

REQUIRED_FM = ["id", "type", "level", "difficulty", "tags", "source", "version", "updated_at", "unit_title"]

BAND_RANGES = {
    "score-000-060": (0, 60),
    "score-061-080": (61, 80),
    "score-081-100": (81, 100),
    "score-101-120": (101, 120),
}

CHAPTER_SIZE = 10


def parse_frontmatter(text: str):
    if not text.startswith("---\n"):
        return None, text
    end = text.index("\n---\n")
    fields = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields, text[end + 5:]


def main() -> int:
    errors, warnings = [], []
    words_by_band: dict[str, dict[str, str]] = {}
    total_words = 0
    files = sorted(CONTENT_DIR.rglob("unit-*.md"))

    if not files:
        print("No content files found under content/")
        return 1

    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        fm, body = parse_frontmatter(path.read_text(encoding="utf-8"))

        if fm is None:
            errors.append(f"{rel}: missing frontmatter")
            continue

        for key in REQUIRED_FM:
            if not fm.get(key):
                errors.append(f"{rel}: missing frontmatter field '{key}'")

        band_dir = path.parent.name
        band_id = fm.get("score_band_id", "")
        if band_id != band_dir:
            errors.append(f"{rel}: score_band_id '{band_id}' != directory '{band_dir}'")
        if band_id in BAND_RANGES:
            lo, hi = BAND_RANGES[band_id]
            if fm.get("score_min") != str(lo) or fm.get("score_max") != str(hi):
                errors.append(f"{rel}: score_min/max do not match band {band_id}")
        else:
            errors.append(f"{rel}: unknown band '{band_id}'")

        if not re.match(r"^voca-\d{3}-\d{3}-u\d{3}$", fm.get("id", "")):
            warnings.append(f"{rel}: id '{fm.get('id')}' does not follow voca-XXX-XXX-uNNN")

        band_words = words_by_band.setdefault(band_id, {})
        count = 0
        for lineno, line in enumerate(body.splitlines(), 1):
            stripped = line.strip()
            if not stripped.startswith("- "):
                continue
            count += 1
            parts = [p.strip() for p in stripped[2:].split("|")]
            if len(parts) != 6:
                errors.append(f"{rel}:{lineno}: expected 6 fields, got {len(parts)}")
                continue
            word, meaning, pron, hint, example, translation = parts
            for name, value in [("word", word), ("meaning", meaning),
                                ("example", example), ("translation", translation)]:
                if not value:
                    errors.append(f"{rel}:{lineno}: empty {name}")
            if not pron:
                warnings.append(f"{rel}:{lineno}: '{word}' has no pronunciation")
            if not hint:
                warnings.append(f"{rel}:{lineno}: '{word}' has no hint")
            key = word.lower()
            if key in band_words:
                errors.append(f"{rel}:{lineno}: duplicate word '{word}' (also in {band_words[key]})")
            else:
                band_words[key] = rel

        total_words += count
        if count % CHAPTER_SIZE != 0:
            warnings.append(f"{rel}: {count} words is not a multiple of {CHAPTER_SIZE} (chapter size)")

    # Cross-band duplicates are allowed but reported
    seen: dict[str, str] = {}
    for band, words in words_by_band.items():
        for word in words:
            if word in seen and seen[word] != band:
                warnings.append(f"'{word}' appears in both {seen[word]} and {band}")
            else:
                seen[word] = band

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")

    band_summary = ", ".join(f"{b.split('-', 1)[1]}: {len(w)}" for b, w in sorted(words_by_band.items()))
    print(f"\n{len(files)} files, {total_words} words ({band_summary})")
    print(f"{len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
