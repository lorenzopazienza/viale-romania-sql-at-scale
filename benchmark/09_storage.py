"""Experiment 9: how much space the table and the index take at each size."""
from common import connect, save

TIERS = ["big_10k", "big_100k", "big_1m", "big_10m"]


def main():
    out = []
    for db in TIERS:
        cur = connect(db).cursor()
        cur.execute("ANALYZE TABLE access_log")
        cur.fetchall()
        cur.execute("SELECT COUNT(*) FROM access_log")
        rows = cur.fetchone()[0]
        cur.execute("""SELECT index_name, stat_value * @@innodb_page_size / 1024 / 1024
                       FROM mysql.innodb_index_stats
                       WHERE database_name = %s AND table_name = 'access_log' AND stat_name = 'size'""",
                    (db,))
        sizes = {name: round(float(mb), 2) for name, mb in cur.fetchall()}
        rec = {"db": db, "rows": rows, "table_mb": sizes.get("PRIMARY"),
               "index_mb": sizes.get("idx_loc_date_time")}
        print(rec, flush=True)
        out.append(rec)
    save("exp9_storage.json", out)


if __name__ == "__main__":
    main()
