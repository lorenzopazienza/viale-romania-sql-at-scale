"""Experiment 8: what does protecting access_log cost at insert time?

Three copies of the access_log schema receive the same 200,000 valid swipes:
  plain    no check (the lab's schema)
  fk       FOREIGN KEY (badge_id) REFERENCES badges
  trigger  AFTER INSERT trigger that logs unknown badges to security_alerts
Then one unregistered swipe is sent to each, to show how each design reacts.
"""
import statistics
import time

import pymysql

from common import connect, save

N = 200000
REPS = 3

SCHEMA = """(access_id INT PRIMARY KEY, badge_id VARCHAR(10) NOT NULL, location VARCHAR(30) NOT NULL,
            access_date DATE NOT NULL, entry_time TIME NOT NULL, exit_time TIME NULL{extra})"""

TRIGGER = """CREATE TRIGGER trg_unknown_badge AFTER INSERT ON log_trigger FOR EACH ROW
BEGIN
  IF NOT EXISTS (SELECT 1 FROM badges WHERE badge_id = NEW.badge_id) THEN
    INSERT INTO security_alerts (access_id, badge_id, location, alert_at, reason)
    VALUES (NEW.access_id, NEW.badge_id, NEW.location,
            TIMESTAMP(NEW.access_date, NEW.entry_time), 'UNKNOWN BADGE');
  END IF;
END"""

GHOST_ROW = "(99999999, 'B-9147', 'Room 204', '2026-09-21', '19:37:00', '19:48:00')"


def main():
    cur = connect().cursor()
    cur.execute("DROP DATABASE IF EXISTS trigbench")
    cur.execute("CREATE DATABASE trigbench")
    cur.execute("USE trigbench")
    cur.execute("CREATE TABLE badges (badge_id VARCHAR(10) PRIMARY KEY, student_id INT NOT NULL)")
    cur.execute("INSERT INTO badges SELECT badge_id, student_id FROM big_10m.badges")
    cur.execute("CREATE TABLE src " + SCHEMA.format(extra=""))
    cur.execute(f"""INSERT INTO src SELECT a.* FROM big_10m.access_log a
                    JOIN big_10m.badges b ON b.badge_id = a.badge_id
                    WHERE a.access_id BETWEEN 1000 AND {1000 + N * 2} LIMIT {N}""")
    cur.execute("CREATE TABLE log_plain " + SCHEMA.format(extra=""))
    cur.execute("CREATE TABLE log_fk " + SCHEMA.format(
        extra=", FOREIGN KEY (badge_id) REFERENCES badges(badge_id)"))
    cur.execute("CREATE TABLE log_trigger " + SCHEMA.format(extra=""))
    cur.execute("""CREATE TABLE security_alerts (alert_id INT AUTO_INCREMENT PRIMARY KEY,
                   access_id INT, badge_id VARCHAR(10), location VARCHAR(30),
                   alert_at DATETIME, reason VARCHAR(100))""")
    cur.execute(TRIGGER)

    out = {"rows_inserted": N, "variants": [], "ghost_swipe": []}
    for table in ("log_plain", "log_fk", "log_trigger"):
        times = []
        for _ in range(REPS):
            cur.execute(f"TRUNCATE TABLE {table}")
            t = time.perf_counter()
            cur.execute(f"INSERT INTO {table} SELECT * FROM src")
            times.append(time.perf_counter() - t)
        sec = statistics.median(times)
        rec = {"variant": table.replace("log_", ""), "seconds": round(sec, 2),
               "rows_per_s": round(N / sec)}
        print(rec, flush=True)
        out["variants"].append(rec)

    cur.execute("TRUNCATE TABLE security_alerts")
    for table in ("log_plain", "log_fk", "log_trigger"):
        try:
            cur.execute(f"INSERT INTO {table} VALUES {GHOST_ROW}")
            outcome = "accepted"
        except pymysql.err.IntegrityError as e:
            outcome = f"rejected: error {e.args[0]}"
        out["ghost_swipe"].append({"variant": table.replace("log_", ""), "outcome": outcome})
    cur.execute("SELECT badge_id, location, alert_at, reason FROM security_alerts")
    out["alerts_logged"] = [list(map(str, r)) for r in cur.fetchall()]
    print(out["ghost_swipe"], out["alerts_logged"], flush=True)
    save("exp8_trigger_cost.json", out)


if __name__ == "__main__":
    main()
