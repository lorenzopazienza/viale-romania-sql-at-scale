"""Experiment 4: the case queries at 10k, 100k, 1M and 10M swipes, without and with an index.

Queries:
  ghost       step 3, the unregistered badge in Room 204 (LEFT JOIN ... IS NULL)
  except      step 10, course version (EXCEPT)
  case        the whole case in one CTE query (case_all_in_one_slow.sql)
  case_fixed  the same query with LIMIT 1 in crime_window (case_all_in_one_fixed.sql)

Every query must return the same rows with and without the index.
"""
import json
import os
import time

from common import connect, time_query, save, RESULTS_DIR

HERE = os.path.dirname(os.path.abspath(__file__))
TIERS = os.environ.get("TIERS", "big_10k,big_100k,big_1m,big_10m").split(",")
INDEX = "CREATE INDEX idx_loc_date_time ON access_log (location, access_date, entry_time)"

Q = {
    "ghost": """SELECT a.* FROM access_log a
LEFT JOIN badges b ON b.badge_id = a.badge_id
WHERE b.badge_id IS NULL AND a.location = 'Room 204' AND a.access_date = '2026-09-21'""",
    "except": """SELECT b.student_id FROM access_log a JOIN badges b ON b.badge_id = a.badge_id
WHERE a.location = 'Main Entrance' AND a.access_date = '2026-09-21'
  AND a.entry_time <= '19:37:00' AND a.exit_time >= '19:48:00'
EXCEPT
SELECT att.student_id FROM attendance att JOIN lectures l ON l.lecture_id = att.lecture_id
WHERE l.lecture_date = '2026-09-21' AND l.start_time <= '19:37:00' AND l.end_time >= '19:48:00'
EXCEPT
SELECT b.student_id FROM access_log a JOIN badges b ON b.badge_id = a.badge_id
WHERE a.access_date = '2026-09-21' AND a.location IN ('Library', 'Gym')
  AND a.entry_time <= '19:37:00' AND a.exit_time >= '19:48:00'""",
    "case": open(os.path.join(HERE, "case_all_in_one_slow.sql")).read(),
    "case_fixed": open(os.path.join(HERE, "case_all_in_one_fixed.sql")).read(),
}


def drop_secondary(cur):
    cur.execute("SHOW INDEX FROM access_log")
    for name in sorted({r[2] for r in cur.fetchall() if r[2] != "PRIMARY"}):
        cur.execute(f"DROP INDEX {name} ON access_log")


def main():
    out = []
    for db in TIERS:
        cur = connect(db).cursor()
        cur.execute("SELECT COUNT(*) FROM access_log")
        rec = {"db": db, "rows": cur.fetchone()[0]}
        drop_secondary(cur)
        answers = {}
        big = rec["rows"] > 5e6
        for name, sql in Q.items():
            sec, rows = time_query(cur, sql, reps=1 if big and name == "case" else 3 if big else 5)
            rec[name + "_noidx_ms"] = round(sec * 1000, 2)
            answers[name] = sorted(map(str, rows))
        t = time.perf_counter()
        cur.execute(INDEX)
        rec["index_build_s"] = round(time.perf_counter() - t, 1)
        cur.execute("ANALYZE TABLE access_log")
        cur.fetchall()
        for name, sql in Q.items():
            sec, rows = time_query(cur, sql, reps=1 if big and name == "case" else 5)
            rec[name + "_idx_ms"] = round(sec * 1000, 2)
            assert sorted(map(str, rows)) == answers[name], (db, name)
        rec["case_answer"] = answers["case"]
        print(rec, flush=True)
        out.append(rec)
    path = os.path.join(RESULTS_DIR, "exp4_scaling.json")
    if os.path.exists(path):  # keep tiers that were not re-run
        done = {r["db"] for r in out}
        out = [r for r in json.load(open(path)) if r["db"] not in done] + out
        out.sort(key=lambda r: r["rows"])
    save("exp4_scaling.json", out)


if __name__ == "__main__":
    main()
