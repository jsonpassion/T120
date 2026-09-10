#!/usr/bin/env python3
"""Generate manifest.json from the content/ tree.

Walks content/<type>/<band>/unit-NNN.md, reads each file's frontmatter,
computes real SHA-256 checksums (the app uses them as change-detection
tokens: a changed checksum triggers re-download), and writes manifest.json.

The manifest `version` is derived from the combined content hash, so it
changes exactly when any content file changes.

Usage:
    python3 tools/build_manifest.py            # writes manifest.json
    python3 tools/build_manifest.py --check    # verify manifest is current
"""

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content"
MANIFEST_PATH = ROOT / "manifest.json"

TRACK = "toefl-120"
SCHEMA_VERSION = 1

# Must match the app's hardcoded ScoreBandInfo.allBands.
SCORE_BANDS = [
    {"id": "score-000-060", "label": "~60",     "min_score": 0,   "max_score": 60,  "order": 1},
    {"id": "score-061-080", "label": "61-80",   "min_score": 61,  "max_score": 80,  "order": 2},
    {"id": "score-081-100", "label": "81-100",  "min_score": 81,  "max_score": 100, "order": 3},
    {"id": "score-101-120", "label": "101-120", "min_score": 101, "max_score": 120, "order": 4},
]

PROFILE = {
    "target_score": 120,
    "daily_study_minutes": 5,
    "voca_review_rule": "hoedok-rounds",
    # Chapters per band that stay free before the full-access purchase.
    # Remote-configurable: the app reads this from the manifest profile.
    "free_chapters": 3,
}


def parse_frontmatter(text: str) -> dict:
    if not text.startswith("---\n"):
        raise ValueError("missing frontmatter")
    end = text.index("\n---\n")
    fields = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields


def build_entries() -> list:
    entries = []
    for path in sorted(CONTENT_DIR.rglob("unit-*.md")):
        rel = path.relative_to(ROOT).as_posix()
        raw = path.read_bytes()
        fm = parse_frontmatter(raw.decode("utf-8"))

        match = re.search(r"unit-(\d+)\.md$", path.name)
        sequence = int(match.group(1)) if match else 0

        entries.append({
            "id": fm["id"],
            "type": fm["type"],
            "level": int(fm["level"]),
            "path": rel,
            "checksum_sha256": hashlib.sha256(raw).hexdigest(),
            "updated_at": fm["updated_at"],
            "score_band_id": fm.get("score_band_id"),
            "score_min": int(fm["score_min"]) if fm.get("score_min") else None,
            "score_max": int(fm["score_max"]) if fm.get("score_max") else None,
            "unit_title": fm.get("unit_title"),
            "unit_title_ko": fm.get("unit_title_ko"),
            "unit_symbol": fm.get("unit_symbol"),
            "sequence": sequence,
        })
    return entries


def content_version(entries: list) -> str:
    combined = hashlib.sha256(
        "".join(e["checksum_sha256"] for e in entries).encode()
    ).hexdigest()
    return f"c-{combined[:12]}"


def build_manifest() -> dict:
    entries = build_entries()
    return {
        "version": content_version(entries),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "schema_version": SCHEMA_VERSION,
        "track": TRACK,
        "profile": PROFILE,
        "score_band_policy": {"version": "3.0", "rule": "four-tier", "bands": SCORE_BANDS},
        "entries": entries,
    }


def main() -> int:
    manifest = build_manifest()

    if "--check" in sys.argv:
        if not MANIFEST_PATH.exists():
            print("manifest.json is missing — run tools/build_manifest.py")
            return 1
        current = json.loads(MANIFEST_PATH.read_text())
        if current.get("version") != manifest["version"]:
            print("manifest.json is stale — run tools/build_manifest.py")
            return 1
        print("manifest.json is up to date")
        return 0

    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(f"Wrote manifest.json — version {manifest['version']}, {len(manifest['entries'])} entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
