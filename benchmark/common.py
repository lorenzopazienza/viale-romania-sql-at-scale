"""Shared helpers for the benchmark scripts.

Connection settings come from environment variables:
  MYSQL_HOST (default localhost), MYSQL_USER (bench), MYSQL_PASSWORD (bench)
"""
import json
import os
import statistics
import time

import pymysql

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")


def connect(database=None):
    return pymysql.connect(
        host=os.environ.get("MYSQL_HOST", "localhost"),
        user=os.environ.get("MYSQL_USER", "bench"),
        password=os.environ.get("MYSQL_PASSWORD", "bench"),
        database=database,
        autocommit=True,
    )


def time_query(cur, sql, reps=5, limit_ms=None):
    """Median wall-clock time (s) of `reps` warm runs, after one warm-up run.

    Returns (median_seconds, rows). With limit_ms set, a run that exceeds it is
    stopped by MySQL and (None, error message) is returned.
    """
    if limit_ms:
        cur.execute(f"SET SESSION max_execution_time = {int(limit_ms)}")
    try:
        cur.execute(sql)
        rows = cur.fetchall()
        times = []
        for _ in range(reps):
            t = time.perf_counter()
            cur.execute(sql)
            cur.fetchall()
            times.append(time.perf_counter() - t)
        return statistics.median(times), rows
    except pymysql.err.OperationalError as e:
        return None, str(e)[:80]
    finally:
        if limit_ms:
            cur.execute("SET SESSION max_execution_time = 0")


def rows_read(cur, sql):
    """Rows the storage engine handed to the server for one run (Handler_read_*)."""
    cur.execute("FLUSH STATUS")
    cur.execute(sql)
    cur.fetchall()
    cur.execute("SHOW SESSION STATUS LIKE 'Handler_read%'")
    return sum(int(v) for _, v in cur.fetchall())


def explain_first_lines(cur, sql, n=6):
    cur.execute("EXPLAIN ANALYZE " + sql)
    text = cur.fetchone()[0]
    return "\n".join(text.splitlines()[:n])


def save(name, data):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = os.path.join(RESULTS_DIR, name)
    with open(path, "w") as f:
        json.dump(data, f, indent=1, default=str)
    print("saved", os.path.relpath(path))
