# Viale Romania: SQL at scale

Follow-up to **Lab 5, SQL Murder Mystery** (Databases and Big Data, Luiss).

In the lab, a student is found dead in Room 204 and the case is solved with SQL over a small university database: 136 students, 486 badge swipes. Every query answers in milliseconds, so every query looks equally good.

This repository asks what happens to the same queries when the campus is real-sized. I generated a campus with **10 million badge swipes** around the original case, re-ran every step on MySQL 8.0, read the execution plans, and measured.

![Step 3 query time vs table size](docs/img/scaling_ghost.png)

## Findings

| | finding | numbers (10M swipes) | details |
|---|---|---|---|
| 1 | One composite index turns a full-year scan into a lookup of one room on one night. | 4,014 ms → 19.7 ms (204×) | [Indexes](docs/01-indexes.md) |
| 2 | The wrong index is worse than none: an index on `location` alone doubles the time. | no index 4.1 s, `(location)` 8.7 s | [Indexes](docs/01-indexes.md) |
| 3 | Solving the whole case in one elegant CTE query was the slowest option, and the index made it slower. The optimizer recomputed the crime window 13,511 times. One `LIMIT 1` fixes it. | 92,455 ms → 59.5 ms (1,554×) | [CTEs and the optimizer](docs/02-cte-and-the-optimizer.md) |
| 4 | The correlated subquery of step 8 is quadratic; a window function is not. | 10,000 grades: 23.1 s vs 24.3 ms | [Correlated subqueries](docs/03-correlated-subqueries.md) |
| 5 | `NOT EXISTS` and `NOT IN` get the same plan and beat `LEFT JOIN ... IS NULL`; `NOT IN` silently returns nothing if the list contains a `NULL`. | 9.6 s vs 12.8 s; 0 rows vs 986 | [Anti-joins](docs/04-anti-joins.md) |
| 6 | The murder was possible because `access_log` has no foreign key. A foreign key would destroy the evidence; a trigger keeps it and raises an alert at 19:37, at 3.8× the insert cost. | 149k → 39k inserts/s | [Schema design](docs/05-schema-design.md) |

## Author

**Lorenzo Pazienza**
Visiting student, Stanford University

BSc in Management and Artificial Intelligence, Luiss Guido Carli

Optimization, High-Performance Computing, AI Systems

https://github.com/lorenzopazienza/

https://www.linkedin.com/in/lorenzo-pazienza/

## The case

| | |
|---|---|
| **Who** | Tommaso Arcuri (student_id 203) |
| **How** | Unregistered badge `B-9147`, Room 204, 21/09/2026, in at 19:37, out at 19:48 |
| **Why** | Jealousy: Ginevra Loreti left him on 30/07 and started dating the victim on 20/08 |

Every step is solved twice in `solutions/`: with the SQL the lab teaches, and with a rewrite using window functions, CTEs, self-joins and anti-joins. [docs/walkthrough.md](docs/walkthrough.md) explains each query.

## Repository

```
solutions/
  00_accusation.sql          the accusation and the queries that prove it
  01_steps_basic.sql         the 11 steps of the browser game, course techniques
  02_steps_advanced.sql      the same 11 steps rewritten, plus a recursive CTE and a suspicion score
docs/
  walkthrough.md             every step explained
  methodology.md             data generation, timing protocol, limits
  01-indexes.md ... 05-schema-design.md   one page per finding
  img/                       charts (generated)
benchmark/
  01_generate_campus.sql     10M-swipe campus around the original rows
  02_busy_murder_day.sql     a normal day's traffic on 21/09 that does not change the answer
  03_build_tiers.sh          10k / 100k / 1M copies
  check_data.sql             distribution checks on the generated data
  04_scaling.py ... 09_storage.py   one script per experiment
  explain_plans.py           EXPLAIN ANALYZE output quoted in the docs
  design/                    foreign key and trigger demos on the lab database
  run_all.sh                 every experiment in order
analysis/make_charts.py      results/*.json -> docs/img/*.png
tests/test_solutions.py      every solution checked on MySQL and SQLite
results/                     raw measurements (JSON) and plans
Makefile
```

## Experiments

| script | question | output |
|---|---|---|
| `04_scaling.py` | How do the case queries grow from 10k to 10M rows, with and without an index? | `exp4_scaling.json` |
| `05_correlated_vs_window.py` | Correlated subquery vs `RANK()` from 1k to 200k grades | `exp5_correlated_vs_window.json` |
| `06_index_design.py` | Seven index variants on the 10M table: time, rows read, size, build time | `exp6_index_design.json` |
| `07_anti_joins.py` | `LEFT JOIN`/`NOT EXISTS`/`NOT IN`/`EXCEPT` over 10M rows, and the `NULL` trap | `exp7_anti_joins.json` |
| `08_trigger_cost.py` | Insert throughput with no check, a foreign key, a trigger | `exp8_trigger_cost.json` |
| `09_storage.py` | Table and index size at each scale | `exp9_storage.json` |

Setup: MySQL 8.0.46, 2 vCPU, 2 GB buffer pool, warm cache, median of repeated runs. The generated data is deterministic and checked after every build; the first version of the generator produced correlated columns and was replaced (see [methodology](docs/methodology.md)).

## Reproduce

Requirements: MySQL 8.0.31 or later (for `EXCEPT`), Python 3.10+, and the lab dump `DEMO_luiss_mystery.sql`, which belongs to the course and is not included here.

```bash
pip install -r requirements.txt
# a MySQL user for the Python scripts (defaults: bench / bench)
mysql -uroot -e "CREATE USER 'bench'@'localhost' IDENTIFIED BY 'bench'; GRANT ALL ON *.* TO 'bench'@'localhost';"

make setup DUMP=path/to/DEMO_luiss_mystery.sql   # load the lab database
make test  DUMP=path/to/DEMO_luiss_mystery.sql   # check every solution (MySQL + SQLite)
make data  DUMP=path/to/DEMO_luiss_mystery.sql   # build the 10M-swipe campus (a few minutes)
make bench                                       # run all experiments (about 30 minutes)
make charts                                      # redraw docs/img from results/
```

`make test` runs 6 tests: the three solution files on both engines. It checks each step's rows (for example, that step 10 returns only student 203 and that the recursive CTE shows `B-9147` in the room from 19:37 to 19:48), not just that the queries run.

## Limits

One machine, uniform synthetic data, warm cache, one MySQL version. The orders of magnitude and the plans are the point; the exact ratios would change with skewed real data, cold caches or another optimizer. [Methodology](docs/methodology.md) has the details.