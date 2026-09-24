-- Synthetic campus around the original case.
-- Prerequisite: the lab dump loaded as database big_10m
--   sed 's/luiss_mystery/big_10m/g' DEMO_luiss_mystery.sql | mysql -uroot
--
-- Pseudo-random values come from CRC32 of a salted row number, e.g.
-- CRC32(CONCAT('loc', n)). This is deterministic (same data on every run) and,
-- unlike RAND(seed) with consecutive seeds, gives independent columns.
-- Takes a few minutes on 2 vCPU.
USE big_10m;
SET SESSION cte_max_recursion_depth = 20000;

DROP TABLE IF EXISTS seq;
CREATE TABLE seq (n INT PRIMARY KEY);
INSERT INTO seq
WITH RECURSIVE r AS (SELECT 0 AS n UNION ALL SELECT n + 1 FROM r WHERE n < 9999)
SELECT n FROM r;

-- 50,000 synthetic students + one badge each
INSERT INTO students
SELECT 1000 + n, CONCAT('Name', n), CONCAT('Surname', n),
       ELT(1 + CRC32(CONCAT('prog', n)) % 3, 'Data Management Class', 'Global Data Lab', 'Economics'),
       2023 + CRC32(CONCAT('year', n)) % 4
FROM (SELECT a.n * 10000 + b.n AS n FROM seq a JOIN seq b WHERE a.n < 5) t;

INSERT INTO badges
SELECT CONCAT('X-', LPAD(student_id - 1000, 7, '0')), student_id, '2025-09-10'
FROM students WHERE student_id >= 1000;

-- 10,000,000 synthetic swipes from 2025-09-01 to 2026-09-20 (never on the murder night).
-- About 1 in 10,000 uses an unregistered card (G-xxxxx) as noise.
INSERT INTO access_log (access_id, badge_id, location, access_date, entry_time, exit_time)
SELECT 1000 + n,
       IF(CRC32(CONCAT('ghost', n)) % 10000 = 0,
          CONCAT('G-', LPAD(CRC32(CONCAT('gid', n)) % 100000, 5, '0')),
          CONCAT('X-', LPAD(CRC32(CONCAT('badge', n)) % 50000, 7, '0'))),
       ELT(1 + CRC32(CONCAT('loc', n)) % 4, 'Main Entrance', 'Library', 'Gym', 'Room 204'),
       DATE_ADD('2025-09-01', INTERVAL CRC32(CONCAT('day', n)) % 385 DAY),
       SEC_TO_TIME(t_in),
       SEC_TO_TIME(LEAST(t_in + 300 + CRC32(CONCAT('stay', n)) % 10800, 86399))
FROM (
  SELECT n, 25200 + CRC32(CONCAT('in', n)) % 50400 AS t_in
  FROM (SELECT a.n * 10000 + b.n AS n FROM seq a JOIN seq b WHERE a.n < 1000) s
) x;
