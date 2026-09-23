# Viale Romania: SQL at scale

Follow-up to **Lab 5, SQL Murder Mystery** (Databases and Big Data, Luiss).

In class the case is solved on 486 badge swipes and every query answers in a few milliseconds.
I wanted to see what happens to the same queries on a campus with **10 million swipes**, so I generated
one around the original case and measured.

The course materials (case dump, browser game, lab slides) are not included.
To reproduce, use `DEMO_luiss_mystery.sql` from the lab.

## The case

| | |
|---|---|
| **Who** | Tommaso Arcuri (student_id 203) |
| **How** | Unregistered badge `B-9147`, Room 204, 21/09/2026, 19:37 to 19:48 |
| **Why** | Jealousy: Ginevra Loreti left him on 30/07 and started dating the victim on 20/08 |

## Repository

```
solutions/
  00_accusation.sql       accusation sheet and the queries that prove it (MySQL)
  01_steps_basic.sql      the 11 steps of the browser game, course techniques
  02_steps_advanced.sql   the same 11 steps with window functions, CTEs, a recursive CTE, self/anti-joins
docs/
  walkthrough.md          step-by-step explanation of every query
benchmark/                data generator, tier builder, benchmark scripts, design experiments
results/                  raw timings (JSON) and EXPLAIN ANALYZE output
```

## Setup

MySQL 8.0.46, 2 vCPU, `innodb_buffer_pool_size` = 2 GB. Timings are the median of warm runs (3 to 5), measured from Python with pymysql.

Synthetic campus: 50,136 students, 10,027,486 swipes from 1 Sep 2025 to the murder night (27,000 of them on the murder day, all finished before 19:30), 967 random unregistered cards as noise.
The case query returns Tommaso Arcuri at every size.

## Results

### 1. One composite index, 190x faster (step 3, ghost badge)

```sql
CREATE INDEX idx_loc_date_time ON access_log (location, access_date, entry_time);
```

| rows | no index | with index |
|---:|---:|---:|
| 10,513 | 3.8 ms | 0.4 ms |
| 100,756 | 30.9 ms | 0.7 ms |
| 1,003,186 | 323 ms | 1.8 ms |
| 10,027,486 | 3,147 ms | 16.6 ms |

`EXPLAIN ANALYZE` (in `results/`): a table scan over 10M rows to keep 6,757 (about 3 s) becomes an index lookup that reads only those 6,757 (9.5 ms).
Column order follows the filters: `location` and `access_date` are equality conditions, `entry_time` is a range, so it goes last.

### 2. The "elegant" query was the slowest (10M rows, index in place)

| query | time |
|---|---:|
| Course version with `EXCEPT` (step 10) | 33 ms |
| Whole case in one CTE query (`benchmark/case_all_in_one_slow.sql`) | 21,728 ms |
| Same query with `LIMIT 1` inside `crime_window` (`benchmark/case_all_in_one_fixed.sql`) | 44 ms |

The one-query version derives the crime window from the ghost badge instead of hard-coding 19:37 and 19:48.
On 10M rows it took 21.7 s, slower than without the index (17.4 s).
The plan (`results/explain_case_slow.txt`) shows the optimizer merging the CTE into the join and re-reading the Room 204 rows **13,510 times**, once per Library/Gym swipe.
With `LIMIT 1` the CTE is materialized once, its two times become constants, and the index can use them: 496x faster.

### 3. Correlated subquery vs window function (step 8)

| grades | correlated subquery | + index (course_id, grade) | `RANK() OVER (PARTITION BY course_id)` |
|---:|---:|---:|---:|
| 1,000 | 210 ms | 46 ms | 3.6 ms |
| 10,000 | 19.2 s | 4.5 s | 30 ms |
| 50,000 | stopped at 60 s | stopped at 60 s | 152 ms |
| 200,000 | stopped at 60 s | stopped at 60 s | 942 ms |

The correlated version recomputes `MIN()` for every row. At 10,000 grades that is 10,000 × 2,500 = 25 million index reads. The index makes each read cheaper but the cost is still quadratic. The window function sorts each course once.

### 4. Root cause: schema design

`access_log.badge_id` has no foreign key, which is how an unregistered card got into Room 204.

- Adding the foreign key fails (`ERROR 1452`) because orphan swipes already exist. It would also make the reader discard unknown cards, which are evidence.
- A trigger that writes unknown badges to a `security_alerts` table keeps every swipe and flags `B-9147` at 19:37:00, eleven minutes before it leaves the room.

See `benchmark/06_foreign_key_attempt.sql` and `benchmark/07_trigger_alert.sql`.

## Reproduce

```bash
# 1. load the lab dump as big_10m
sed 's/luiss_mystery/big_10m/g' DEMO_luiss_mystery.sql | mysql -uroot

# 2. generate the campus (about 2 minutes)
mysql -uroot < benchmark/01_generate_campus.sql
mysql -uroot < benchmark/02_busy_murder_day.sql

# 3. smaller tiers: big_10k, big_100k, big_1m
./benchmark/03_build_tiers.sh

# 4. benchmarks (pip install pymysql; a MySQL user bench/bench with access to these databases)
cd benchmark
python3 04_bench_access_log.py
python3 05_bench_grades.py
```

All queries in `solutions/` run both in the browser game (SQLite 3.45) and on MySQL 8.0.
