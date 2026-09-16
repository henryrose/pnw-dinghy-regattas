# PNW Dinghy Regattas 2027

Annual ILCA, 505 and Flying Scot regattas within reach of Port Townsend, WA, with projected 2027 dates, drive distance, class starts, adult eligibility, and a link to each event's Notice of Race.

Open `index.html` in a browser. It's a single self-contained page (Google Fonts are the only external request).

## Notes

- 2027 dates are projections from past years unless marked confirmed.
- Eligibility and class notes come from each event's most recent Notice of Race (mostly 2026). Re-check when 2027 NORs are published.
- Class tags: solid = the class is named in the NOR with its own start; dashed = the class races only under the stated condition.

## Updating

`index.html` is a build artifact — don't hand-edit it. The event data lives in `data/events.json`; the page shell lives in `templates/index.template.html`.

```
# Check every event's NOR link is still reachable, and look for a newer
# one on any event that has an `infoUrl` set. Dry run: reports only.
python3 scripts/update_events.py

# Same, but write back any confidently-detected NOR link changes.
python3 scripts/update_events.py --apply

# Check a single event.
python3 scripts/update_events.py --only frigid-digit

# Regenerate index.html from data/events.json + the template.
python3 scripts/build.py
```

`update_events.py` only ever touches `nor`, `norYear`, `lastChecked`, and `linkStatus`. It never rewrites `eligibility`, `verdict`, `classes`, or dates — reading a new NOR for eligibility changes is a human job. When it flags a NOR link as broken or finds a newer one, read the new document and update the event's fields in `data/events.json` by hand, then run `scripts/build.py`.

Each event can optionally have an `infoUrl`: a stable regatta-listing page (separate from the NOR file itself) that the update script can crawl to discover next year's NOR before you know its exact filename. Most events don't have one set yet, since NOR files are often re-uploaded yearly to hash-named CDN paths with no stable index page — for those, the script just health-checks the existing link.
