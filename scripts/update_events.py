#!/usr/bin/env python3
"""Check (and optionally update) NOR links for every event in data/events.json.

For each event this:
  - fetches its stored `nor` URL and records whether it's still reachable
  - if the event has an `infoUrl` (a stable regatta-listing page, separate from
    the NOR file itself), scans that page for links that look like a newer
    Notice of Race and reports them as candidates
  - with --apply, swaps in a candidate NOR link when exactly one confident
    match is found, and stamps norYear accordingly

It never touches `eligibility`, `verdict`, `classes`, or dates on its own —
those require actually reading the new NOR, which is a human job. When a NOR
link changes, re-read it and update those fields by hand, then re-run
scripts/build.py.

Usage:
  python3 scripts/update_events.py                # dry run, report only
  python3 scripts/update_events.py --apply         # also update nor/norYear
  python3 scripts/update_events.py --only some-id  # check a single event
"""
import argparse
import datetime
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "events.json"

USER_AGENT = (
    "Mozilla/5.0 (compatible; PNWDinghyRegattaChecker/1.0; "
    "+https://henryrose.github.io/pnw-dinghy-regattas/)"
)
TIMEOUT = 15
NOR_LINK_RE = re.compile(r'href=["\']([^"\']+)["\']', re.I)
NOR_KEYWORD_RE = re.compile(r'nor|notice.?of.?race', re.I)


def fetch(url, timeout=TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            content_type = resp.headers.get("Content-Type", "")
            body = b""
            if "html" in content_type or "text" in content_type:
                body = resp.read(2_000_000)
            return status, content_type, body, None
    except urllib.error.HTTPError as e:
        return e.code, "", b"", str(e)
    except Exception as e:  # noqa: BLE001 - network can fail in many ways
        return None, "", b"", str(e)


def find_nor_candidates(base_url, html_bytes, current_nor, next_year):
    try:
        text = html_bytes.decode("utf-8", errors="replace")
    except Exception:
        return []
    candidates = []
    for href in NOR_LINK_RE.findall(text):
        if not NOR_KEYWORD_RE.search(href):
            continue
        absolute = urllib.parse.urljoin(base_url, href)
        if absolute == current_nor:
            continue
        if str(next_year) in absolute and absolute not in candidates:
            candidates.append(absolute)
    return candidates


def check_event(event, apply_changes, today):
    name = event["name"]
    nor = event.get("nor")
    result = {"id": event["id"], "name": name, "notes": []}

    if not nor:
        result["notes"].append("no NOR link on file (TBA)")
        event["lastChecked"] = today
        event["linkStatus"] = "n/a"
        return result

    status, _ctype, _body, err = fetch(nor)
    if status == 200:
        event["linkStatus"] = "ok"
        result["notes"].append("NOR link OK")
    elif status is not None:
        event["linkStatus"] = f"broken ({status})"
        result["notes"].append(f"NOR link returned {status} — find the new one manually")
    else:
        event["linkStatus"] = "error"
        result["notes"].append(f"could not fetch NOR link: {err}")
    event["lastChecked"] = today

    info_url = event.get("infoUrl")
    if info_url:
        # Guess the year we'd expect a fresh NOR to reference.
        current_year_match = re.search(r"20\d{2}", event.get("norYear") or "")
        next_year = int(current_year_match.group()) + 1 if current_year_match else datetime.date.today().year
        i_status, i_ctype, i_body, i_err = fetch(info_url)
        if i_status == 200 and "html" in i_ctype:
            candidates = find_nor_candidates(info_url, i_body, nor, next_year)
            if len(candidates) == 1:
                result["notes"].append(f"found candidate {next_year} NOR: {candidates[0]}")
                if apply_changes:
                    event["nor"] = candidates[0]
                    event["norYear"] = f"{next_year} NOR (auto-updated {today}, re-verify eligibility)"
                    result["notes"].append("APPLIED — re-read this NOR and update eligibility/verdict/classes by hand")
            elif len(candidates) > 1:
                result["notes"].append(
                    f"found {len(candidates)} possible {next_year} NOR links, pick one manually: "
                    + ", ".join(candidates)
                )
        elif i_status != 200:
            result["notes"].append(f"infoUrl unreachable ({i_status or i_err})")

    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="write detected NOR link changes back to data/events.json")
    parser.add_argument("--only", metavar="ID", help="only check the event with this id")
    parser.add_argument("--sleep", type=float, default=1.0, help="politeness delay between requests, in seconds")
    args = parser.parse_args()

    data = json.loads(DATA_PATH.read_text())
    events = data["events"]
    today = datetime.date.today().isoformat()

    targets = [e for e in events if not args.only or e["id"] == args.only]
    if args.only and not targets:
        sys.exit(f"no event with id {args.only!r}")

    results = []
    for i, event in enumerate(targets):
        results.append(check_event(event, args.apply, today))
        if i < len(targets) - 1:
            time.sleep(args.sleep)

    width = max((len(r["name"]) for r in results), default=0)
    for r in results:
        print(f"{r['name']:<{width}}  " + " / ".join(r["notes"]))

    DATA_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"\n{'Applied changes and ' if args.apply else ''}updated lastChecked/linkStatus for {len(targets)} event(s) in {DATA_PATH.relative_to(ROOT)}")
    if not args.apply:
        print("Dry run — pass --apply to write any detected NOR link changes.")
    print("Run scripts/build.py to regenerate index.html after any data changes.")


if __name__ == "__main__":
    main()
