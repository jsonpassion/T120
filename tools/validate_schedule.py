#!/usr/bin/env python3
"""Validate schedule.json (official exam sittings) against the app's reader.

Format and update procedure: SCHEDULE.md. The app (ExamSchedule.swift) drops a single
malformed session or window instead of failing, so a typo silently hides a sitting —
this script is where such mistakes must surface.

Errors (must be 0 before pushing):
- schema 1, exam name, updatedAt / every date is a real yyyy-MM-dd
- URLs are https
- regions: unique ids, localized names, ISO country codes, at most one "default"
- sessions: unique ids per region, localized titles, examDate; registration windows with
  start <= end and closing no later than the exam; resultDate after the exam
- levels only name band ids that exist in content/ (content/voca/<band> or content/<lang>/voca/<band>), or in levels.json
- selfScheduled tests carry no sessions

Warnings: sittings on or before today (the app already ignores them — prune them), regions
with no upcoming sitting, updatedAt older than 45 days, titles without ko or en.

After the checks it prints the app view: every region and sitting exactly as the app will
list it on that day (SHOW / HIDE, D-day, registration state, which region each device country
gets). It is the same reading rule as the app — parity/run.sh in the app repo diffs it against
ExamSchedule.swift itself.

Usage: python3 tools/validate_schedule.py [--today YYYY-MM-DD] [--app-view] [path/to/schedule.json]
  --today     judge as if the learner's calendar showed that day (default: today)
  --app-view  print only the app view
"""

import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LANGS = {"en", "ko", "ja", "zh", "vi"}
errors, warnings = [], []


def err(where, msg):
    errors.append(f"{where}: {msg}")


def warn(where, msg):
    warnings.append(f"{where}: {msg}")


def day(value, where, required=True):
    if value is None:
        if required:
            err(where, "missing date")
        return None
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        err(where, f"not yyyy-MM-dd: {value!r}")
        return None
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        err(where, f"impossible date: {value}")
        return None


def url(value, where):
    if value is None:
        return
    if not isinstance(value, str) or not value.startswith("https://"):
        err(where, f"URL must be https: {value!r}")


def text(value, where, required=True):
    if value is None:
        if required:
            err(where, "missing text")
        return
    if isinstance(value, str):
        if not value.strip():
            err(where, "empty text")
        return
    if not isinstance(value, dict) or not value:
        err(where, "text must be a string or {lang: text}")
        return
    for lang, s in value.items():
        if lang not in LANGS:
            err(where, f"unknown language key {lang!r} (use {sorted(LANGS)})")
        if not isinstance(s, str) or not s.strip():
            err(where, f"empty text for {lang}")
    if not ({"ko", "en"} & set(value)):
        warn(where, "no ko or en text — other languages fall back to it")


# ---- What the app will show -------------------------------------------------
# A line-for-line mirror of NINE90/Models/ExamSchedule.swift: the same lenient reading
# (a bad session or window is dropped, a bad optional field becomes empty), the same
# date rule (a sitting counts only while its exam day is after today), the same
# registration state and region choice. Tools/content-kit/parity/run.sh diffs this
# output against the Swift model itself, so the two cannot drift apart silently.

DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def app_day(value):
    if not isinstance(value, str) or not DATE_RE.fullmatch(value):
        return None
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        return None


def app_int(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def app_text(value):
    if isinstance(value, str):
        return {"": value}
    if isinstance(value, dict) and all(isinstance(v, str) for v in value.values()):
        return value
    return None


def app_optional(obj, key, reader):
    """decodeIfPresent inside try?: missing, null or unreadable all become None."""
    return reader(obj[key]) if key in obj and obj[key] is not None else None


def app_window(w):
    if not isinstance(w, dict):
        return None
    # label is decodeIfPresent without try?: present but unreadable drops the window
    if w.get("label") is not None and app_text(w["label"]) is None:
        return None
    start, end = app_day(w.get("start")), app_day(w.get("end"))
    if start is None or end is None:
        return None
    return (start, end)


def app_session(s):
    if not isinstance(s, dict) or not isinstance(s.get("id"), str):
        return None
    if app_text(s.get("title")) is None:
        return None
    exam = app_day(s.get("examDate"))
    if exam is None:
        return None
    raw = s.get("registration")
    windows = sorted(w for w in (map(app_window, raw) if isinstance(raw, list) else []) if w)
    levels = app_optional(s, "levels", lambda v: v if isinstance(v, list) and all(isinstance(x, str) for x in v) else None)
    return {"id": s["id"], "exam": exam, "windows": windows,
            "result": app_optional(s, "resultDate", app_day), "levels": levels}


def app_region(r):
    if not isinstance(r, dict) or not isinstance(r.get("id"), str) or app_text(r.get("name")) is None:
        return None
    countries = r.get("countries")
    countries = countries if isinstance(countries, list) and all(isinstance(c, str) for c in countries) else []
    default = r.get("default") if isinstance(r.get("default"), bool) else False
    raw = r.get("sessions")
    sessions = [x for x in (map(app_session, raw) if isinstance(raw, list) else []) if x]
    return {"id": r["id"], "countries": countries, "default": default, "sessions": sessions}


def app_registration_state(windows, today):
    if not windows:
        return "none"
    for start, end in windows:
        if end >= today:
            return f"opens:{(start - today).days}" if today < start else f"open:{(end - today).days}"
    return "closed"


def app_region_for(regions, device_region):
    for r in regions:
        if device_region in r["countries"]:
            return r
    return next((r for r in regions if r["default"]), regions[0] if regions else None)


def app_view(data, today):
    """The schedule as the app reads it on `today`, one fact per line."""
    lines = [f"TODAY {today}"]
    schema = app_int(data.get("schema")) if isinstance(data, dict) else None
    if schema is None or not isinstance(data.get("exam"), str):
        return lines + ["UNREADABLE (the app keeps its previous copy)"]
    if schema > 1:
        return lines + [f"IGNORED schema {schema} is newer than the app (it keeps its previous copy)"]
    self_scheduled = data.get("selfScheduled") if isinstance(data.get("selfScheduled"), bool) else False
    lines.append(f"SCHEDULE exam={data['exam']} selfScheduled={int(self_scheduled)} updatedAt={app_optional(data, 'updatedAt', app_day) or '-'}")
    raw = data.get("regions")
    regions = [x for x in (map(app_region, raw) if isinstance(raw, list) else []) if x]
    for r in regions:
        lines.append(f"REGION {r['id']} default={int(r['default'])} countries={','.join(r['countries']) or '-'} sessions={len(r['sessions'])}")
        ordered = sorted(r["sessions"], key=lambda s: (s["exam"], s["id"]))
        for s in ordered:
            if s["exam"] > today:
                levels = ",".join(s["levels"]) if s["levels"] is not None else "all"
                lines.append(f"  SHOW {s['id']} {s['exam']} D-{(s['exam'] - today).days} reg={app_registration_state(s['windows'], today)} "
                             f"windows={len(s['windows'])} levels={levels} result={s['result'] or '-'}")
        for s in ordered:
            if s["exam"] <= today:
                lines.append(f"  HIDE {s['id']} {s['exam']}")
    for country in sorted({c for r in regions for c in r["countries"]}):
        lines.append(f"DEVICE {country} -> {app_region_for(regions, country)['id']}")
    fallback = app_region_for(regions, "ZZ")
    lines.append(f"DEVICE other -> {fallback['id'] if fallback else '-'}")
    return lines


def band_ids():
    ids = set()
    for voca in list(ROOT.glob("content/voca")) + list(ROOT.glob("content/*/voca")):
        ids.update(p.name for p in voca.iterdir() if p.is_dir())
    # Public site repos no longer carry the words (they ship inside the app): levels.json lists the band ids.
    if not ids and (ROOT / "levels.json").exists():
        ids.update(json.loads((ROOT / "levels.json").read_text()))
    return ids


def main():
    args = sys.argv[1:]
    today = dt.date.today()
    if "--today" in args:
        i = args.index("--today")
        today = dt.date.fromisoformat(args[i + 1])
        del args[i:i + 2]
    only_app_view = "--app-view" in args
    args = [a for a in args if a != "--app-view"]
    path = Path(args[0]) if args else ROOT / "schedule.json"
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR {path}: {e}")
        return 1
    if only_app_view:
        print("\n".join(app_view(data, today)))
        return 0
    if not isinstance(data, dict):
        print(f"ERROR {path}: top level must be an object")
        return 1

    if app_int(data.get("schema")) != 1:
        err("schema", f"must be the integer 1, got {data.get('schema')!r}")
    if not isinstance(data.get("exam"), str) or not data["exam"].strip():
        err("exam", "missing exam name")
    updated = day(data.get("updatedAt"), "updatedAt")
    if updated and (today - updated).days > 45:
        warn("updatedAt", f"{updated} is {(today - updated).days} days old")
    url(data.get("officialURL"), "officialURL")
    self_scheduled = data.get("selfScheduled", False)
    if not isinstance(self_scheduled, bool):
        err("selfScheduled", "must be true/false")
    text(data.get("note"), "note", required=False)

    regions = data.get("regions")
    if not isinstance(regions, list) or not regions:
        err("regions", "need at least one region")
        regions = []
    bands = band_ids()
    seen_regions, defaults = set(), 0
    for r_index, region in enumerate(regions):
        if not isinstance(region, dict):
            err(f"regions[{r_index}]", "must be an object")
            continue
        rid = region.get("id")
        where = f"regions[{r_index}]({rid})"
        if not isinstance(rid, str) or not rid:
            err(where, "missing id")
        elif rid in seen_regions:
            err(where, "duplicate region id")
        seen_regions.add(rid)
        text(region.get("name"), f"{where}.name")
        countries = region.get("countries", [])
        if not isinstance(countries, list) or any(not isinstance(c, str) or not re.fullmatch(r"[A-Z]{2}", c) for c in countries):
            err(where, f"countries must be ISO 3166 alpha-2 codes: {countries!r}")
        if "default" in region and not isinstance(region["default"], bool):
            err(where, "default must be true/false")
        if region.get("default") is True:
            defaults += 1
        url(region.get("officialURL"), f"{where}.officialURL")

        sessions = region.get("sessions", [])
        if not isinstance(sessions, list):
            err(where, "sessions must be a list")
            continue
        if self_scheduled and sessions:
            err(where, "selfScheduled exams must not list sessions")
        seen, upcoming, previous = set(), 0, None
        for s_index, session in enumerate(sessions):
            if not isinstance(session, dict):
                err(f"{where}.sessions[{s_index}]", "must be an object")
                continue
            sid = session.get("id")
            sw = f"{where}.sessions[{s_index}]({sid})"
            if not isinstance(sid, str) or not sid:
                err(sw, "missing id")
            elif sid in seen:
                err(sw, "duplicate session id in this region")
            seen.add(sid)
            text(session.get("title"), f"{sw}.title")
            exam = day(session.get("examDate"), f"{sw}.examDate")
            if exam:
                if exam <= today:
                    warn(sw, f"exam day {exam} is today or past — the app ignores it; remove it")
                else:
                    upcoming += 1
                if previous and exam < previous:
                    warn(sw, "sessions are not in date order")
                previous = exam
            windows = session.get("registration", [])
            if not isinstance(windows, list):
                err(sw, "registration must be a list")
                windows = []
            last_end = None
            for w_index, window in enumerate(windows):
                ww = f"{sw}.registration[{w_index}]"
                if not isinstance(window, dict):
                    err(ww, "must be an object")
                    continue
                start = day(window.get("start"), f"{ww}.start")
                end = day(window.get("end"), f"{ww}.end")
                text(window.get("label"), f"{ww}.label", required=False)
                if start and end and start > end:
                    err(ww, f"start {start} is after end {end}")
                if end and exam and end > exam:
                    err(ww, f"closes {end} after the exam {exam}")
                if start and last_end and start < last_end:
                    warn(ww, "windows overlap or are out of order")
                last_end = end or last_end
            result = day(session.get("resultDate"), f"{sw}.resultDate", required=False)
            if result and exam and result <= exam:
                err(sw, f"resultDate {result} is not after the exam {exam}")
            levels = session.get("levels")
            if levels is not None:
                if not isinstance(levels, list) or not levels:
                    err(sw, "levels must be a non-empty list of band ids (omit for all levels)")
                elif bands:
                    unknown = [l for l in levels if l not in bands]
                    if unknown:
                        err(sw, f"unknown band ids {unknown} (have {sorted(bands)})")
            text(session.get("note"), f"{sw}.note", required=False)
            url(session.get("url"), f"{sw}.url")
        if not self_scheduled and upcoming == 0:
            warn(where, "no upcoming sitting — the app shows the official link and date entry only")
    if defaults > 1:
        err("regions", "more than one region marked default")

    for w in warnings:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    print("--- app view (what the app shows on this day; same rules as ExamSchedule.swift) ---")
    print("\n".join(app_view(data, today)))
    print(f"{path.name}: {len(errors)} errors, {len(warnings)} warnings (today {today})")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
