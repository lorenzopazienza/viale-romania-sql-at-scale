# Murder at Viale Romania — SQL at scale

Follow-up to **Lab 5 · SQL Murder Mystery** (Databases and Big Data, Luiss).
The case is solved in class on 486 badge swipes. This repo asks what happens to the same queries
on a campus with **10 million swipes**, and measures it.

> The course materials (case dump, browser game, lab slides) belong to the course and are **not** included.
> To reproduce, use `DEMO_luiss_mystery.sql` from the lab.

## The case

| | |
|---|---|
| **Who** | Tommaso Arcuri (student_id 203) |
| **How** | Unregistered badge `B-9147`, Room 204, 21/09/2026, 19:37–19:48 |
| **Why** | Jealousy: Ginevra Loreti left him on 30/07 and started dating the victim on 20/08 |

## Repository

```
solutions/
  00_accusation.sql       the accusation sheet with the queries that prove it (MySQL)
  01_steps_basic.sql      the 11 steps of the browser game, course techniques
  02_steps_advanced.sql   the same 11 steps with window functions, CTEs, recursive CTE, self/anti-joins
docs/
  spiegazione_step.md     step-by-step explanation (Italian)
benchmark/                data generator + benchmark scripts
results/                  raw timings (JSON) and EXPLAIN ANALYZE plans
```

## Results

MySQL 8.0.46 · 2 vCPU · 2 GB InnoDB buffer pool · median of warm runs.
Synthetic campus: 50,136 students, 10,027,486 swipes (1 Sep 2025 → murder night), 967 random ghost cards as noise.
The case query returns Tommaso Arcuri at every size.

### 1 · One composite index: 190× faster (step 3, ghost badge)

`CREATE INDEX idx_loc_date_time ON access_log (location, access_date, entry_time);`

| rows | no index | with index |
|---:|---:|---:|
| 10,513 | 3.8 ms | 0.4 ms |
| 100,756 | 30.9 ms | 0.7 ms |
| 1,003,186 | 323 ms | 1.8 ms |
| 10,027,486 | 3,147 ms | 16.6 ms |

`EXPLAIN ANALYZE`: table scan over 10M rows (3,038 ms) → index lookup of 6,757 rows (9.5 ms).

### 2 · The elegant query was the slowest (10M rows, index in place)

| query | time |
|---|---:|
| Course version, `EXCEPT` (step 10) | 33 ms |
| All-in-one CTE (whole case in one query) | 21,728 ms |
| Same CTE + `LIMIT 1` inside `crime_window` | 44 ms |

The optimizer merged the `crime_window` CTE into the join and re-evaluated it **13,510 times**
(once per Library/Gym swipe — see `results/plan_slow.txt`). `LIMIT 1` makes it materialize once,
so 19:37 / 19:48 become constants usable by the index: **496×** faster.

### 3 · Correlated subquery vs window function (step 8)

| grades | correlated subquery | + index (course_id, grade) | `RANK() OVER (PARTITION BY course_id)` |
|---:|---:|---:|---:|
| 1,000 | 210 ms | 46 ms | 3.6 ms |
| 10,000 | 19.2 s | 4.5 s | 30 ms |
| 50,000 | stopped at 60 s | stopped at 60 s | 152 ms |
| 200,000 | stopped at 60 s | stopped at 60 s | 942 ms |

The correlated version recomputes `MIN()` per row: 10,000 × 2,500 = 25M index reads.

### 4 · Root cause: schema design

`access_log.badge_id` has no foreign key. Adding one fails (`ERROR 1452`, orphan rows exist) and would
also discard evidence. A trigger that logs unknown badges into `security_alerts` flags `B-9147` at 19:37:00.

## Reproduce

```bash
# 1. load the lab dump into a database called big_10m
sed 's/luiss_mystery/big_10m/g' DEMO_luiss_mystery.sql | mysql -uroot
# 2. generate the synthetic campus (~2 min)
mysql -uroot < benchmark/1_generate_10M.sql
mysql -uroot < benchmark/2_busy_murder_day.sql
# 3. smaller tiers big_10k / big_100k / big_1m: same tables, access_log filtered by access_id
#    (access_id < 1000 are the original rows; see 3_bench_access_log.py for the tier names)
# 4. benchmarks (pip install pymysql; MySQL user bench/bench)
cd benchmark && python3 3_bench_access_log.py && python3 4_bench_grades.py
```

The game's engine is SQLite 3.45 (sql.js); every query in `solutions/` was tested there and on MySQL 8.0.
