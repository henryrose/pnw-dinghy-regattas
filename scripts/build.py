#!/usr/bin/env python3
"""Render index.html from templates/index.template.html + data/events.json."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "events.json"
TEMPLATE_PATH = ROOT / "templates" / "index.template.html"
OUT_PATH = ROOT / "index.html"

# Fields the front-end actually reads. Bookkeeping fields used by
# update_events.py (id, infoUrl, lastChecked, linkStatus) stay out of the
# published page.
PUBLIC_FIELDS = [
    "month", "day", "dateLabel", "tag", "classes", "name", "where", "miles",
    "far", "status", "verdict", "eligibility", "nor", "norYear",
    "norIsPageOnly", "alt", "altLabel",
]

PLACEHOLDER = re.compile(r"/\*__EVENTS_DATA__\*/.*?/\*__EVENTS_DATA_END__\*/", re.S)


def main():
    data = json.loads(DATA_PATH.read_text())
    events = [{k: e.get(k) for k in PUBLIC_FIELDS} for e in data["events"]]
    payload = json.dumps(events, ensure_ascii=False, indent=1)

    template = TEMPLATE_PATH.read_text()
    if not PLACEHOLDER.search(template):
        sys.exit("build.py: placeholder /*__EVENTS_DATA__*/ ... /*__EVENTS_DATA_END__*/ not found in template")

    out = PLACEHOLDER.sub(lambda _: payload, template, count=1)
    OUT_PATH.write_text(out)
    print(f"Wrote {OUT_PATH.relative_to(ROOT)} from {len(events)} events in {DATA_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
