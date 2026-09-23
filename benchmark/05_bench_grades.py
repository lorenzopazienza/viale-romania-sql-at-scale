import pymysql,time,statistics,json
c=pymysql.connect(user='bench',password='bench',autocommit=True); cur=c.cursor()
cur.execute("DROP DATABASE IF EXISTS gbench"); cur.execute("CREATE DATABASE gbench"); cur.execute("USE gbench")
CORR="""SELECT DISTINCT s.student_id, s.first_name, s.last_name FROM {g} g JOIN big_10m.students s ON s.student_id = g.student_id
WHERE g.grade = (SELECT MIN(g2.grade) FROM {g} g2 WHERE g2.course_id = g.course_id)"""
WIN="""SELECT DISTINCT student_id, first_name, last_name FROM (
  SELECT s.student_id, s.first_name, s.last_name,
         RANK() OVER (PARTITION BY g.course_id ORDER BY g.grade) AS pos
  FROM {g} g JOIN big_10m.students s ON s.student_id = g.student_id) t WHERE pos = 1"""
out={}
def timeit(q,reps=3,limit_ms=60000):
    try:
        cur.execute(f"SET SESSION max_execution_time={limit_ms}")
        t=time.perf_counter(); cur.execute(q); r=cur.fetchall(); first=time.perf_counter()-t
        if first>5: return first, r
        ts=[first]
        for _ in range(reps-1):
            t=time.perf_counter(); cur.execute(q); cur.fetchall(); ts.append(time.perf_counter()-t)
        return statistics.median(ts), r
    except pymysql.err.OperationalError as e:
        return None, str(e)[:60]
for N in [1000,10000,50000,200000]:
    g=f"grades_{N}"
    cur.execute(f"CREATE TABLE {g} (grade_id INT PRIMARY KEY, student_id INT NOT NULL, course_id INT NOT NULL, grade INT NOT NULL, KEY (course_id))")
    cur.execute(f"""INSERT INTO {g} SELECT n, 1000 + (n % 50000), 1 + FLOOR(RAND(n)*4), 18 + FLOOR(RAND(n+1)*13)
                   FROM (SELECT a.n*10000+b.n AS n FROM big_10m.seq a JOIN big_10m.seq b WHERE a.n*10000+b.n < {N}) x""")
    cur.execute(f"ANALYZE TABLE {g}"); cur.fetchall()
    r={}
    r['corr'],res1=timeit(CORR.format(g=g))
    r['window'],res2=timeit(WIN.format(g=g))
    cur.execute(f"CREATE INDEX idx_course_grade ON {g} (course_id, grade)"); cur.execute(f"ANALYZE TABLE {g}"); cur.fetchall()
    r['corr_idx'],res3=timeit(CORR.format(g=g))
    r['same']= (sorted(res2)==sorted(res3)) and (res1 is None or isinstance(res1,str) or sorted(res1)==sorted(res2))
    r['n_result']=len(res2)
    out[N]=r; print(N,r,flush=True)
json.dump(out,open('../results/bench_grades.json','w'),indent=1)
