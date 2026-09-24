"""Experiment 6: which index? Same two queries, one index variant at a time.

Runs on big_10m. Drops every secondary index on access_log, then for each variant:
build it, record build time and size, time the queries, count rows read.
Restores idx_loc_date_time at the end.
"""
import time

from common import connect, time_query, rows_read, explain_first_lines, save

GHOST = """SELECT a.* FROM access_log a
LEFT JOIN badges b ON b.badge_id = a.badge_id
WHERE b.badge_id IS NULL AND a.location = 'Room 204' AND a.access_date = '2026-09-21'"""

INSIDE = """SELECT a.badge_id FROM access_log a
WHERE a.location = 'Main Entrance' AND a.access_date = '2026-09-21'
  AND a.entry_time <= '19:37:00' AND a.exit_time >= '19:48:00'"""

VARIANTS = [
    ("none", None),
    ("(access_date)", "access_date"),
    ("(location)", "location"),
    ("(location, access_date)", "location, access_date"),
    ("(location, access_date, entry_time)", "location, access_date, entry_time"),
    ("(entry_time, location, access_date)", "entry_time, location, access_date"),
    ("(location, access_date, entry_time, exit_time, badge_id)",
     "location, access_date, entry_time, exit_time, badge_id"),
]


def secondary_indexes(cur):
    cur.execute("SHOW INDEX FROM access_log")
    return sorted({r[2] for r in cur.fetchall() if r[2] != "PRIMARY"})


def index_size_mb(cur, name):
    cur.execute("""SELECT stat_value * @@innodb_page_size / 1024 / 1024
                   FROM mysql.innodb_index_stats
                   WHERE database_name = DATABASE() AND table_name = 'access_log'
                     AND index_name = %s AND stat_name = 'size'""", (name,))
    r = cur.fetchone()
    return round(float(r[0]), 1) if r else 0.0


def main():
    cur = connect("big_10m").cursor()
    for name in secondary_indexes(cur):
        cur.execute(f"DROP INDEX {name} ON access_log")
    out = []
    for label, cols in VARIANTS:
        rec = {"index": label}
        if cols:
            t = time.perf_counter()
            cur.execute(f"CREATE INDEX idx_exp ON access_log ({cols})")
            rec["build_s"] = round(time.perf_counter() - t, 1)
            cur.execute("ANALYZE TABLE access_log")
            cur.fetchall()
            rec["size_mb"] = index_size_mb(cur, "idx_exp")
        for qname, sql in (("ghost", GHOST), ("inside", INSIDE)):
            sec, rows = time_query(cur, sql, reps=3 if not cols else 5)
            rec[qname + "_ms"] = round(sec * 1000, 2)
            rec[qname + "_rows_returned"] = len(rows)
            rec[qname + "_rows_read"] = rows_read(cur, sql)
            rec[qname + "_plan"] = explain_first_lines(cur, sql)
        print(label, {k: v for k, v in rec.items() if not k.endswith("_plan")}, flush=True)
        out.append(rec)
        if cols:
            cur.execute("DROP INDEX idx_exp ON access_log")
    cur.execute("CREATE INDEX idx_loc_date_time ON access_log (location, access_date, entry_time)")
    save("exp6_index_design.json", out)


if __name__ == "__main__":
    main()
