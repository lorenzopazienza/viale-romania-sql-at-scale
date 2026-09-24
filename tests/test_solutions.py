"""Checks that every query in solutions/ returns the expected rows,
on MySQL (database luiss_mystery) and on SQLite (the browser game's engine).

    LUISS_DUMP=path/to/DEMO_luiss_mystery.sql pytest -q tests/

MySQL settings: MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD (defaults: localhost, bench, bench).
If MySQL is not reachable, the MySQL tests are skipped.
"""
import os
import re
import sqlite3

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DUMP = os.environ.get("LUISS_DUMP", os.path.join(ROOT, "DEMO_luiss_mystery.sql"))
TOMMASO = 203


# ---------------------------------------------------------------- parsing
def statements(path):
    """Yields (label, sql) for every statement in a solutions file.

    The label is the last 'STEP n' / 'BONUS n' / 'Variant' heading seen in a
    comment, plus a running index for statements under the same heading.
    """
    label, count, buf = "top", {}, []
    for line in open(path, encoding="utf-8"):
        m = re.match(r"--\s*(STEP \d+|BONUS \d+)", line.strip())
        if m:
            label = m.group(1)
        elif line.strip().startswith("-- Variant"):
            label = label + " variant"
        if not buf and (not line.strip() or line.strip().startswith("--")):
            continue
        buf.append(line)
        if line.rstrip().endswith(";"):
            sql = "".join(buf).strip().rstrip(";")
            buf = []
            if not sql or sql.upper().startswith("USE "):
                continue
            count[label] = count.get(label, 0) + 1
            yield f"{label} #{count[label]}", sql


def rows_as_dicts(cur):
    if cur.description is None:
        return []
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


# ---------------------------------------------------------------- engines
def sqlite_db():
    if not os.path.exists(DUMP):
        pytest.skip(f"lab dump not found at {DUMP} (set LUISS_DUMP)")
    sql = open(DUMP, encoding="utf-8").read()
    sql = re.sub(r"^(SET NAMES|DROP DATABASE|CREATE DATABASE|USE ).*$", "", sql, flags=re.M)
    sql = sql.replace("COLLATE utf8mb4_unicode_ci", "")
    con = sqlite3.connect(":memory:")
    con.executescript(sql)
    return con


def mysql_db():
    pymysql = pytest.importorskip("pymysql")
    try:
        return pymysql.connect(
            host=os.environ.get("MYSQL_HOST", "localhost"),
            user=os.environ.get("MYSQL_USER", "bench"),
            password=os.environ.get("MYSQL_PASSWORD", "bench"),
            database="luiss_mystery",
            autocommit=True,
        )
    except pymysql.err.OperationalError as e:
        pytest.skip(f"MySQL not reachable: {e}")


@pytest.fixture(params=["sqlite", "mysql"])
def run(request):
    con = sqlite_db() if request.param == "sqlite" else mysql_db()

    def _run(path):
        cur = con.cursor()
        cur.execute("DROP TABLE IF EXISTS solution")
        out = {}
        for label, sql in statements(os.path.join(ROOT, path)):
            cur.execute(sql)
            out[label] = rows_as_dicts(cur)
        return out

    yield _run
    con.close()


def ids(rows, col="student_id"):
    return {r[col] for r in rows}


# ---------------------------------------------------------------- expectations
STEP_CHECKS = {
    "STEP 1": lambda r: [x["report_id"] for x in r] == [8],
    "STEP 2": lambda r: ids(r) == {3, 4, 5, 6, 201},
    "STEP 4": lambda r: ids(r) == {203, 204, 5} and r[0]["student_id"] == TOMMASO,
    "STEP 5": lambda r: ids(r) == {203, 205},
    "STEP 6": lambda r: ids(r) == {204, 209, 213},
    "STEP 7": lambda r: len(r) == 15
    and {x["student_id"]: x["points_behind"] for x in r}[203] == 1
    and {x["student_id"]: x["points_behind"] for x in r}[204] == 12,
    "STEP 8": lambda r: ids(r) == {204, 211},
    "STEP 9": lambda r: ids(r) == {12, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 204, 206},
    "STEP 10": lambda r: ids(r) == {TOMMASO},
}


def solution_ok(rows):
    (row,) = rows
    return (row["first_name"], row["last_name"], str(row["murder_time"])) == (
        "Tommaso", "Arcuri", "19:37:00") and "Ginevra" in row["motive"]


def test_basic_steps(run):
    res = run("solutions/01_steps_basic.sql")
    for step, check in STEP_CHECKS.items():
        assert check(res[f"{step} #1"]), step
    ghost = res["STEP 3 #1"]
    assert [x["badge_id"] for x in ghost] == ["B-9147"]
    assert res["STEP 11 #2"] == []  # the INSERT


def test_advanced_steps(run):
    res = run("solutions/02_steps_advanced.sql")
    for step, check in STEP_CHECKS.items():
        assert check(res[f"{step} #1"]), step
    timeline = res["STEP 3 #1"]
    assert len(timeline) == 7
    assert [x["badge_id"] for x in timeline if x["status"] == "GHOST"] == ["B-9147"]
    assert [x["badge_id"] for x in res["STEP 3 variant #1"]] == ["B-9147"]
    assert solution_ok(res["STEP 11 #4"])  # SELECT * FROM solution
    minutes = [x["minute"] for x in res["BONUS 1 #1"] if "B-9147" in (x["inside_room_204"] or "")]
    assert (minutes[0], minutes[-1], len(minutes)) == ("19:37:00", "19:48:00", 12)
    score = res["BONUS 2 #1"]
    assert score[0]["student_id"] == TOMMASO and score[0]["suspicion_score"] == 6


def test_accusation(run):
    res = run("solutions/00_accusation.sql")
    labels = list(res)
    ghost_timeline, no_alibi, motive = res[labels[2]], res[labels[4]], res[labels[5]]
    assert "B-9147" in {x["badge_id"] for x in ghost_timeline}
    assert ids(no_alibi) == {TOMMASO}
    assert [x["partner"] for x in motive] == ["Federico", "Tommaso", "Maximilian"]
