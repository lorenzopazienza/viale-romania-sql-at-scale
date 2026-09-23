import pymysql, time, json, statistics, sys
case=open('case_all_in_one_slow.sql').read()
Q={
 'ghost': """SELECT a.* FROM access_log a LEFT JOIN badges b ON b.badge_id = a.badge_id
            WHERE b.badge_id IS NULL AND a.location = 'Room 204' AND a.access_date = '2026-09-21'""",
 'except': """SELECT b.student_id FROM access_log a JOIN badges b ON b.badge_id = a.badge_id
WHERE a.location = 'Main Entrance' AND a.access_date = '2026-09-21'
  AND a.entry_time <= '19:37:00' AND a.exit_time >= '19:48:00'
EXCEPT
SELECT att.student_id FROM attendance att JOIN lectures l ON l.lecture_id = att.lecture_id
WHERE l.lecture_date = '2026-09-21' AND l.start_time <= '19:37:00' AND l.end_time >= '19:48:00'
EXCEPT
SELECT b.student_id FROM access_log a JOIN badges b ON b.badge_id = a.badge_id
WHERE a.access_date = '2026-09-21' AND a.location IN ('Library', 'Gym')
  AND a.entry_time <= '19:37:00' AND a.exit_time >= '19:48:00'""",
 'case': case,
}
def run(cur,q,reps=5):
    cur.execute(q); res=cur.fetchall()        # warm-up
    ts=[]
    for _ in range(reps):
        t=time.perf_counter(); cur.execute(q); cur.fetchall(); ts.append(time.perf_counter()-t)
    return statistics.median(ts), res
out={}
for db in ['big_10k','big_100k','big_1m','big_10m']:
    c=pymysql.connect(user='bench',password='bench',database=db,autocommit=True); cur=c.cursor()
    cur.execute("SELECT COUNT(*) FROM access_log"); n=cur.fetchone()[0]
    cur.execute("SHOW INDEX FROM access_log WHERE Key_name='idx_loc_date_time'")
    if cur.fetchall(): cur.execute("DROP INDEX idx_loc_date_time ON access_log")
    r={'rows':n}
    for k,q in Q.items():
        t,res=run(cur,q, 3 if n>5e6 else 5); r[k+'_noidx']=t; r[k+'_result']=str(res)[:120]
    t=time.perf_counter(); cur.execute("CREATE INDEX idx_loc_date_time ON access_log (location, access_date, entry_time)"); r['index_build']=time.perf_counter()-t
    cur.execute("ANALYZE TABLE access_log"); cur.fetchall()
    for k,q in Q.items():
        t,res=run(cur,q); r[k+'_idx']=t
        assert str(res)[:120]==r[k+'_result'], (k,res)
    out[db]=r; print(db, json.dumps(r, default=str)); sys.stdout.flush()
json.dump(out,open('../results/bench_access_log.json','w'),indent=1,default=str)
