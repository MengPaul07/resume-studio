"""Add new campus JDs to existing fixture."""
import json

with open("tests/fixtures/jds/bytedance_campus_2026.json", encoding="utf-8") as f:
    existing = json.load(f)

new_items = json.load(open("tests/fixtures/jds/bytedance_campus_2026_extras.json", encoding="utf-8"))

existing["items"].extend(new_items["items"])
with open("tests/fixtures/jds/bytedance_campus_2026.json", "w", encoding="utf-8") as f:
    json.dump(existing, f, indent=2, ensure_ascii=False)
print(f"Total: {len(existing['items'])} JDs")
