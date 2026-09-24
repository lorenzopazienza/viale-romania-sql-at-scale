"""Experiment 5: step 8 (lowest grade per course) as a correlated subquery vs RANK().

Synthetic grade tables of 1k, 10k, 50k and 200k rows (4 courses). Each query is
stopped after 60 s. The correlated version is also timed with a composite index
on (course_id, grade).
"""
from common import connect, time_query, save

SIZES = [1000, 10000, 50000, 200000]
LIMIT_MS = 60000

CORR = """SELECT DISTINCT s.student_id FROM {g} g
JOIN big_10m.students s ON s.student_id = g.student_id
WHERE g.grade = (SELECT MIN(g2.grade) FROM {g} g2 WHERE g2.course_id = g.course_id)"""

WINDOW = """SELECT DISTINCT student_id FROM (
  SELECT s.student_id, RANK() OVER (PARTITION BY g.course_id ORDER BY g.grade) AS pos
  FROM {g} g JOIN big_10m.students s ON s.student_id = g.student_id) t
WHERE pos = 1"""


def ms(sec):
    return None if sec is None else round(sec * 1000, 1)


def main():
    cur = connect().cursor()
    cur.execute("DROP DATABASE IF EXISTS gbench")
    cur.execute("CREATE DATABASE gbench")
    cur.execute("USE gbench")
    out = []
    for n in SIZES:
        g = f"grades_{n}"
        cur.execute(f"""CREATE TABLE {g} (grade_id INT PRIMARY KEY, student_id INT NOT NULL,
                        course_id INT NOT NULL, grade INT NOT NULL, KEY (course_id))""")
        cur.execute(f"""INSERT INTO {g}
            SELECT n, 1000 + n % 50000, 1 + CRC32(CONCAT('course', n)) % 4,
                   18 + CRC32(CONCAT('grade', n)) % 13
            FROM (SELECT a.n * 10000 + b.n AS n FROM big_10m.seq a JOIN big_10m.seq b
                  WHERE a.n * 10000 + b.n < {n}) x""")
        cur.execute(f"ANALYZE TABLE {g}")
        cur.fetchall()
        rec = {"grades": n}
        t_corr, r_corr = time_query(cur, CORR.format(g=g), reps=3, limit_ms=LIMIT_MS)
        t_win, r_win = time_query(cur, WINDOW.format(g=g), reps=3, limit_ms=LIMIT_MS)
        cur.execute(f"CREATE INDEX idx_course_grade ON {g} (course_id, grade)")
        t_idx, r_idx = time_query(cur, CORR.format(g=g), reps=3, limit_ms=LIMIT_MS)
        rec.update(correlated_ms=ms(t_corr), window_ms=ms(t_win), correlated_idx_ms=ms(t_idx),
                   students_returned=len(r_win))
        for t, r in ((t_corr, r_corr), (t_idx, r_idx)):
            if t is not None:
                assert sorted(r) == sorted(r_win), n
        print(rec, flush=True)
        out.append(rec)
    save("exp5_correlated_vs_window.json", out)


if __name__ == "__main__":
    main()
