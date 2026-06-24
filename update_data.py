#!/usr/bin/env python3
"""
WC 2026 auto-updater
Fetches latest results from openfootball/worldcup.json (free, no API key)
and merges them into data.json, preserving all our custom stats (xGF, xGA, SoT etc.)
"""
import json, urllib.request, datetime, sys

# ── Team name mapping: openfootball → our names ─────────────────────────
NAME_MAP = {
    "Bosnia & Herzegovina": "Bosnia",
    "Czech Republic":       "Czechia",
    "South Korea":          "S. Korea",
    "South Africa":         "S. Africa",
    "Turkey":               "Turkey",
    "Ivory Coast":          "Ivory Coast",
    "DR Congo":             "DR Congo",
    "Curaçao":              "Curaçao",
    "USA":                  "USA",
}
def norm(name):
    return NAME_MAP.get(name, name)

# ── Fetch live data ──────────────────────────────────────────────────────
print("Fetching openfootball worldcup.json...")
url = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"
req = urllib.request.urlopen(url, timeout=15)
live = json.loads(req.read())
matches = live["matches"]

# Only group-stage matches (have a group field)
group_matches = [m for m in matches if m.get("group")]
print(f"  Found {len(group_matches)} group stage matches, {sum(1 for m in group_matches if m.get('score'))} with scores")

# ── Load our data.json ───────────────────────────────────────────────────
with open("data.json") as f:
    data = json.load(f)

# ── Build lookup: (home, away) → fixture ────────────────────────────────
fix_index = {}
for fix in data["fixtures"]:
    key = (fix["home"], fix["away"])
    fix_index[key] = fix

# ── Merge scores into fixtures ───────────────────────────────────────────
updated = 0
newly_played = 0
for m in group_matches:
    if not m.get("score"):
        continue
    h = norm(m["team1"])
    a = norm(m["team2"])
    hs, as_ = m["score"]["ft"]
    key = (h, a)
    if key not in fix_index:
        # Try adding it as a new fixture entry (MD1 matches we might be missing)
        round_num = int(m["round"].replace("Matchday ", "")) if "Matchday" in m["round"] else 1
        fix = {
            "md": round_num,
            "date": m["date"],
            "home": h,
            "away": a,
            "group": m["group"].replace("Group ", ""),
            "homeScore": hs,
            "awayScore": as_,
            "played": True
        }
        data["fixtures"].append(fix)
        fix_index[key] = fix
        newly_played += 1
        continue
    fix = fix_index[key]
    was_played = fix.get("played", False)
    fix["homeScore"] = hs
    fix["awayScore"] = as_
    fix["played"] = True
    if not was_played:
        newly_played += 1
    updated += 1

print(f"  Updated {updated} existing fixtures, added {newly_played} new")

# ── Count how many matchdays are fully complete ──────────────────────────
from collections import defaultdict
md_status = defaultdict(lambda: {"total": 0, "played": 0})
for fix in data["fixtures"]:
    if fix.get("group"):  # only group stage
        md = fix["md"]
        md_status[md]["total"] += 1
        if fix.get("played"):
            md_status[md]["played"] += 1

current_md = 0
for md in sorted(md_status.keys()):
    s = md_status[md]
    if s["played"] > 0:
        current_md = md
    print(f"  MD{md}: {s['played']}/{s['total']} played")

# ── Update meta ──────────────────────────────────────────────────────────
data["meta"]["last_updated"] = datetime.date.today().isoformat()
data["meta"]["matchday"] = current_md
data["meta"]["auto_updated"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# ── Save ─────────────────────────────────────────────────────────────────
with open("data.json", "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Done — data.json updated (MD{current_md}, {datetime.date.today()})")
