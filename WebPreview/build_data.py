#!/usr/bin/env python3
"""Bundles the game's narrative/world/ecosystem JSON (single source of truth in
Stockholm/Content/Data) plus the stylized preview layout into WebPreview/data.json."""
import json, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "Stockholm" / "Content" / "Data"

def load(rel):
    return json.loads((DATA / rel).read_text(encoding="utf-8"))

eco = load("Ecosystem/stockholm_ecosystem.json")
out = {
    "missions": load("Story/missions_ch1.json")["missions"],
    "dialogues": load("Story/dialogues_ch1.json")["dialogues"],
    "npcs": load("Story/npcs.json")["npcs"],
    "chapters": load("Story/chapters.json")["chapters"],
    "locations": load("World/locations.json")["locations"],
    "districts": load("World/districts.json")["districts"],
    "ecosystem": {"researched_on": eco.get("researched_on"), "entries": eco["entries"]},
    "layout": json.loads((ROOT / "WebPreview" / "layout.json").read_text(encoding="utf-8")),
}
dst = ROOT / "WebPreview" / "data.json"
dst.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(f"wrote {dst} ({dst.stat().st_size // 1024} KB)")
