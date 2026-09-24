"""Writes the EXPLAIN ANALYZE plans quoted in the docs to results/plans/ (big_10m)."""
import os

from common import connect, RESULTS_DIR

HERE = os.path.dirname(os.path.abspath(__file__))
GHOST = """SELECT a.* FROM access_log a LEFT JOIN badges b ON b.badge_id = a.badge_id
WHERE b.badge_id IS NULL AND a.location = 'Room 204' AND a.access_date = '2026-09-21'"""


def write(name, cur, sql):
    cur.execute("EXPLAIN ANALYZE " + sql)
    path = os.path.join(RESULTS_DIR, "plans", name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(cur.fetchone()[0] + "\n")
    print("saved", os.path.relpath(path))


def main():
    cur = connect("big_10m").cursor()
    cur.execute("SHOW INDEX FROM access_log WHERE Key_name = 'idx_loc_date_time'")
    if cur.fetchall():
        cur.execute("DROP INDEX idx_loc_date_time ON access_log")
    write("ghost_no_index.txt", cur, GHOST)
    cur.execute("CREATE INDEX idx_loc_date_time ON access_log (location, access_date, entry_time)")
    write("ghost_with_index.txt", cur, GHOST)
    write("case_slow.txt", cur, open(os.path.join(HERE, "case_all_in_one_slow.sql")).read())
    write("case_fixed.txt", cur, open(os.path.join(HERE, "case_all_in_one_fixed.sql")).read())
    correlated(cur)


def correlated(cur):
    """Step 8 on 10,000 grades with the (course_id, grade) index (needs 05 to have run)."""
    cur.execute("SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'gbench' AND table_name = 'grades_10000'")
    if cur.fetchone()[0]:
        write("correlated_10k_with_index.txt", cur, """SELECT DISTINCT s.student_id
FROM gbench.grades_10000 g JOIN big_10m.students s ON s.student_id = g.student_id
WHERE g.grade = (SELECT MIN(g2.grade) FROM gbench.grades_10000 g2 WHERE g2.course_id = g.course_id)""")


if __name__ == "__main__":
    main()
