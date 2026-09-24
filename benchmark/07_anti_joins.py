"""Experiment 7: four ways to find swipes whose badge belongs to nobody.

Runs on big_10m over the WHOLE year (no date filter), so every variant has to
look at all 10M swipes. Also checks the classic NOT IN trap: one NULL in the
subquery and NOT IN returns nothing.
"""
from common import connect, time_query, explain_first_lines, save

VARIANTS = {
    "LEFT JOIN ... IS NULL": """SELECT a.access_id FROM access_log a
LEFT JOIN badges b ON b.badge_id = a.badge_id
WHERE b.badge_id IS NULL""",
    "NOT EXISTS": """SELECT a.access_id FROM access_log a
WHERE NOT EXISTS (SELECT 1 FROM badges b WHERE b.badge_id = a.badge_id)""",
    "NOT IN": """SELECT a.access_id FROM access_log a
WHERE a.badge_id NOT IN (SELECT badge_id FROM badges)""",
    "EXCEPT (distinct badge_ids)": """SELECT badge_id FROM access_log
EXCEPT
SELECT badge_id FROM badges""",
}

NULL_TRAP = {
    "NOT IN, list contains a NULL": """SELECT COUNT(*) FROM access_log a
WHERE a.badge_id NOT IN (SELECT badge_id FROM badges UNION ALL SELECT NULL)""",
    "NOT EXISTS, same list": """SELECT COUNT(*) FROM access_log a
WHERE NOT EXISTS (SELECT 1 FROM (SELECT badge_id FROM badges UNION ALL SELECT NULL) x
                  WHERE x.badge_id = a.badge_id)""",
}


def main():
    cur = connect("big_10m").cursor()
    out = {"variants": [], "null_trap": []}
    for name, sql in VARIANTS.items():
        sec, rows = time_query(cur, sql, reps=3)
        rec = {"variant": name, "ms": round(sec * 1000, 1), "rows": len(rows),
               "plan": explain_first_lines(cur, sql, 4)}
        print(name, rec["ms"], rec["rows"], flush=True)
        out["variants"].append(rec)
    for name, sql in NULL_TRAP.items():
        cur.execute(sql)
        n = cur.fetchone()[0]
        print(name, n, flush=True)
        out["null_trap"].append({"query": name, "count": n})
    save("exp7_anti_joins.json", out)


if __name__ == "__main__":
    main()
