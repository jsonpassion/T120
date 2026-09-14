# T120

Public site and exam schedule for the T120 app.

```
docs/                       ← web app (GitHub Pages)
privacy.md / terms.md       ← policy sources
schedule.json               ← official exam sittings the app fetches (SCHEDULE.md)
levels.json                 ← band ids the schedule may reference
tools/validate_schedule.py  ← run before every push (0 errors)
```

Words are not here: they ship inside the app, built from a private content repo.
