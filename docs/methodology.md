# Methodology

How the synthetic campus is built, how queries are timed, and what the numbers can and cannot tell you.

## Environment

| | |
|---|---|
| Database | MySQL 8.0.46 (InnoDB), default optimizer settings |
| Machine | 2 vCPU, about 7 GB RAM, Linux (cloud VM) |
| `innodb_buffer_pool_size` | 2 GB (the 10M-row table and its index fit in memory) |
| `innodb_flush_log_at_trx_commit` | 2 (only affects the insert experiment) |
| Client | Python 3, pymysql, timings with `time.perf_counter()` |
| Browser game engine | SQLite 3.45 (sql.js), used only for the correctness tests |

## The synthetic campus

The lab database has 486 swipes. To see how the queries behave at scale, `benchmark/01_generate_campus.sql` adds, around the untouched original rows:

- **50,000 students**, each with one badge (`X-0000000` to `X-0049999`);
- **10,000,000 swipes** spread uniformly over 385 days (1 Sep 2025 to 20 Sep 2026), 4 locations, entry times 07:00 to 21:00 and stays of 5 minutes to 3 hours;
- about **1 swipe in 10,000 with an unregistered card** (`G-xxxxx`), so the ghost badge is not the only orphan row;
- **27,000 extra swipes on the murder day** (`02_busy_murder_day.sql`), all finished before 19:30, so that 21/09 looks like any other day without changing the answer.

`benchmark/03_build_tiers.sh` then builds 10k, 100k and 1M versions with the same students and a prefix of the swipes.

### Pseudo-random values

Every generated value comes from `CRC32` of a salted row number, for example `CRC32(CONCAT('loc', n)) % 4`.

A first version used `RAND(n)`, `RAND(n + 1)`, ... with consecutive seeds. Those streams turned out to be strongly correlated in MySQL: 381 of 385 days had **a single location** and only about 130 distinct badges. The murder day was not affected, but the data was unrealistic, so everything was regenerated and re-measured. `benchmark/check_data.sql` now checks the distribution after every build:

| check | value |
|---|---:|
| swipes | 10,027,486 |
| distinct badges | 51,060 |
| days | 386 |
| swipes per day | 25,538 to 27,074 |
| locations per day (minimum) | 4 |
| distinct badges per day (minimum) | 19,918 |
| swipes per location | about 2.507M each |
| unregistered swipes / cards | 986 / 927 |

At every size the whole-case query still returns Tommaso Arcuri, 19:37:00 (asserted in `04_scaling.py`).

## Timing protocol

- One warm-up run, then the **median of 5 runs** (3 for queries that take several seconds at 10M rows, 1 for the 90-second query). Numbers are warm-cache numbers: the data is already in the buffer pool.
- A query is stopped after **60 s** where noted (`max_execution_time`), and reported as "stopped".
- With and without an index, every query must return **the same rows**; the scripts assert it.
- "Rows read" is the sum of the `Handler_read_*` counters for one run: the rows the storage engine handed to the server, including index lookups.
- Plans come from `EXPLAIN ANALYZE` (`benchmark/explain_plans.py`, saved in `results/plans/`).

## Limits

- **One machine, small absolute numbers.** Below about 1 ms the timings are dominated by client round trips and vary by ±50% between runs; compare orders of magnitude, not decimals.
- **Uniform data.** Real badge logs are skewed (rush hours, popular rooms). Skew changes which index wins; the direction of the results should hold, the exact ratios will not.
- **Warm cache only.** Cold-cache timings (data on disk) would make full scans look even worse.
- **One optimizer version.** The CTE result in [the CTE page](02-cte-and-the-optimizer.md) depends on how MySQL 8.0 decides to merge or materialize a CTE; other versions or databases may choose differently.
