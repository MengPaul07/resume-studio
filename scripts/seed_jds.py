"""Seed the JD library from all JSON fixtures in tests/fixtures/jds/."""
import json
import os
import sys
sys.path.insert(0, ".")

from src.services.rag.jd_repository import JdRepository


def main():
    repo = JdRepository()
    repo.store.clear()
    total = 0

    jds_dir = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures", "jds")
    for fname in sorted(os.listdir(jds_dir)):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(jds_dir, fname)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        items = data.get("items", [])
        count = repo.seed(items)
        total += count
        print(f"  {fname}: {count} items")

    print(f"\nTotal: {total} JDs seeded")
    print(f"Tags: company={_count_tag(repo, 'company')} type={_count_tag(repo, 'recruitment_type')} role={_count_tag(repo, 'role_direction')}")

    # Quick verify
    for q, f in [("后端开发", None), ("算法", None), ("前端", {"recruitment_type": "campus"}), ("产品", {"company": "bytedance"})]:
        r = repo.query(q, top_k=1, filters=f)
        label = f"query='{q}'" + (f" filter={f}" if f else "")
        first = r[0]["text"][:50] if r else "NO RESULTS"
        print(f"  [{label}] → {first}")


def _count_tag(repo: JdRepository, key: str) -> int:
    import sqlite3
    db = repo.store._db_path()
    conn = sqlite3.connect(db)
    n = conn.execute("SELECT COUNT(DISTINCT value) FROM inverted_tags WHERE key=?", (key,)).fetchone()[0]
    return n


if __name__ == "__main__":
    main()
