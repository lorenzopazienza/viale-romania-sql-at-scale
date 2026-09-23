-- Synthetic campus around the original case.
-- Prerequisite: the lab dump loaded as database big_10m
--   sed 's/luiss_mystery/big_10m/g' DEMO_luiss_mystery.sql | mysql -uroot
-- Takes about 90 s on 2 vCPU.
USE big_10m;
SET SESSION cte_max_recursion_depth = 20000;
CREATE TABLE seq (n INT PRIMARY KEY);
INSERT INTO seq WITH RECURSIVE r AS (SELECT 0 AS n UNION ALL SELECT n+1 FROM r WHERE n < 9999) SELECT n FROM r;

-- 50,000 synthetic students + badges
INSERT INTO students
SELECT 1000 + n, CONCAT('Name', n), CONCAT('Surname', n),
       ELT(1 + (n % 3), 'Data Management Class', 'Global Data Lab', 'Economics'), 2023 + (n % 4)
FROM (SELECT a.n*10000 + b.n AS n FROM seq a JOIN seq b WHERE a.n < 5) t;
INSERT INTO badges
SELECT CONCAT('X-', LPAD(student_id - 1000, 7, '0')), student_id, '2025-09-10'
FROM students WHERE student_id >= 1000;

-- 10,000,000 synthetic swipes, never on the night of the murder
INSERT INTO access_log (access_id, badge_id, location, access_date, entry_time, exit_time)
SELECT 1000 + n,
       IF(RAND(n) < 0.0001, CONCAT('G-', LPAD(FLOOR(RAND(n+7)*99999), 5, '0')),     -- rare ghost cards
          CONCAT('X-', LPAD(FLOOR(RAND(n+1)*50000), 7, '0'))),
       ELT(1 + FLOOR(RAND(n+2)*4), 'Main Entrance', 'Library', 'Gym', 'Room 204'),
       d,
       SEC_TO_TIME(t_in),
       SEC_TO_TIME(LEAST(t_in + 300 + FLOOR(RAND(n+4)*10800), 86399))
FROM (
  SELECT n,
         DATE_ADD('2025-09-01', INTERVAL (FLOOR(RAND(n+5)*385) + IF(FLOOR(RAND(n+5)*385) >= 385, 1, 0)) DAY) AS d0,
         25200 + FLOOR(RAND(n+3)*50400) AS t_in
  FROM (SELECT a.n*10000 + b.n AS n FROM seq a JOIN seq b WHERE a.n < 1000) s
) x
CROSS JOIN LATERAL (SELECT IF(x.d0 = '2026-09-21', '2026-09-22', x.d0) AS d) dd;
