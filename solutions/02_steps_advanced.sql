-- #####################################################################
--  Murder at Viale Romania - advanced solutions
--  Same answers as the 11 steps, using techniques beyond the basic course:
--  window functions, CTEs, recursive CTEs, self-joins, anti-joins,
--  INSERT ... WITH ... SELECT.
--  Tested on the game's engine (SQLite 3.45) and on MySQL 8.0.
--  In TablePlus run  USE luiss_mystery;  first.
-- #####################################################################

-- =====================================================================
-- STEP 1 · The report  -  window function: ROW_NUMBER() OVER (PARTITION BY)
-- Basic: ORDER BY ... LIMIT 1 finds the latest report for ONE campus.
-- Here ROW_NUMBER numbers the reports inside each campus; rn = 1 is the
-- latest one. Drop the campus filter and you get the latest report of
-- EVERY campus in a single query.
-- =====================================================================
SELECT report_id, campus, report_date, report_time, crime_type
FROM (
  SELECT r.*,
         ROW_NUMBER() OVER (PARTITION BY campus
                            ORDER BY report_date DESC, report_time DESC) AS rn
  FROM crime_reports r
) AS ranked
WHERE rn = 1 AND campus = 'Viale Romania';

-- =====================================================================
-- STEP 2 · Room 204  -  GROUP BY instead of DISTINCT
-- DISTINCT only removes duplicates. GROUP BY gives one row per person AND
-- extra information: how many times they came in, first and last entry
-- (Max: twice, the last at 18:55).
-- =====================================================================
SELECT s.student_id, s.first_name, s.last_name,
       COUNT(*)           AS swipes,
       MIN(a.entry_time)  AS first_in,
       MAX(a.entry_time)  AS last_in
FROM access_log a
JOIN badges b   ON b.badge_id   = a.badge_id
JOIN students s ON s.student_id = b.student_id
WHERE a.location = 'Room 204' AND a.access_date = '2026-09-21'
GROUP BY s.student_id, s.first_name, s.last_name;

-- =====================================================================
-- STEP 3 · The ghost badge  -  full timeline with LEFT JOIN + CASE
-- Basic: LEFT JOIN + IS NULL isolates the ghost row.
-- Here the whole day in Room 204 is shown and every swipe is labelled with
-- CASE, so the ghost badge appears in context (Max inside from 18:55 with
-- no exit, B-9147 from 19:37 to 19:48).
-- =====================================================================
SELECT a.access_id, a.badge_id, a.entry_time, a.exit_time,
       CASE WHEN s.student_id IS NULL THEN '*** UNKNOWN ***'
            ELSE CONCAT(s.first_name, ' ', s.last_name) END AS owner,
       CASE WHEN b.badge_id IS NULL THEN 'GHOST' ELSE 'ok' END AS status
FROM access_log a
LEFT JOIN badges b   ON b.badge_id   = a.badge_id
LEFT JOIN students s ON s.student_id = b.student_id
WHERE a.location = 'Room 204' AND a.access_date = '2026-09-21'
ORDER BY a.entry_time;

-- Variant: ANTI-JOIN with NOT EXISTS (safe with NULLs, unlike NOT IN).
SELECT a.*
FROM access_log a
WHERE a.location = 'Room 204' AND a.access_date = '2026-09-21'
  AND NOT EXISTS (SELECT 1 FROM badges b WHERE b.badge_id = a.badge_id);

-- =====================================================================
-- STEP 4 · The regulars  -  window functions on top of GROUP BY
-- RANK() gives the ranking; SUM(COUNT(*)) OVER () is the total across all
-- groups, so each student gets a share of visits.
-- Tommaso alone accounts for 40% of the regulars' visits.
-- =====================================================================
SELECT s.student_id, s.first_name, s.last_name,
       COUNT(*) AS visits,
       RANK() OVER (ORDER BY COUNT(*) DESC) AS rnk,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_of_all_visits
FROM access_log a
JOIN badges b   ON b.badge_id   = a.badge_id
JOIN students s ON s.student_id = b.student_id
WHERE a.location = 'Room 204'
  AND a.access_date BETWEEN '2026-09-14' AND '2026-09-20'
GROUP BY s.student_id, s.first_name, s.last_name
HAVING COUNT(*) > 3
ORDER BY visits DESC;

-- =====================================================================
-- STEP 5 · Her past  -  SELF-JOIN instead of a subquery
-- relationships is used twice: "cur" = Max's current relationship,
-- "ex" = the ENDED relationships of the same girlfriend.
-- It also shows when she started dating Max: 30/07 -> 20/08, three weeks.
-- =====================================================================
SELECT ex.student_id, s.first_name, s.last_name,
       ex.start_date, ex.end_date,
       cur.start_date AS she_started_with_max
FROM relationships cur
JOIN relationships ex ON ex.partner_id = cur.partner_id
                     AND ex.end_date IS NOT NULL
JOIN students s ON s.student_id = ex.student_id
WHERE cur.student_id = 201 AND cur.end_date IS NULL
ORDER BY ex.end_date DESC;

-- =====================================================================
-- STEP 6 · Report cards  -  CTE (WITH) instead of a derived table
-- A CTE is a named derived table: easier to read and REUSABLE. Here it is
-- used twice (the filter + the class average for comparison).
-- =====================================================================
WITH student_avg AS (
  SELECT student_id, AVG(grade) AS avg_grade
  FROM grades
  GROUP BY student_id
)
SELECT sa.student_id, s.first_name, s.last_name,
       ROUND(sa.avg_grade, 2) AS avg_grade,
       ROUND(sa.avg_grade - (SELECT AVG(avg_grade) FROM student_avg), 2) AS vs_class_avg
FROM student_avg sa
JOIN students s ON s.student_id = sa.student_id
WHERE sa.avg_grade < 22
ORDER BY sa.avg_grade;

-- =====================================================================
-- STEP 7 · Points behind  -  window function instead of a scalar subquery
-- MAX(CASE WHEN student_id = 201 ...) OVER () copies Max's grade onto every
-- row without a second query. The course is looked up by name instead of
-- hard-coding course_id = 1.
-- The <> 201 filter goes OUTSIDE: inside, the window would no longer see
-- Max's grade.
-- =====================================================================
SELECT student_id, grade, points_behind
FROM (
  SELECT g.student_id, g.grade,
         MAX(CASE WHEN g.student_id = 201 THEN g.grade END) OVER () - g.grade AS points_behind
  FROM grades g
  JOIN courses c ON c.course_id = g.course_id
  WHERE c.course_name = 'Machine Learning'
) AS t
WHERE student_id <> 201
ORDER BY points_behind DESC;

-- =====================================================================
-- STEP 8 · Last in class  -  RANK() OVER (PARTITION BY course)
-- Basic: a correlated subquery recomputes MIN() for every row.
-- Here it is one pass; RANK handles ties (two students tied for last
-- would both get pos = 1).
-- =====================================================================
SELECT DISTINCT student_id, first_name, last_name
FROM (
  SELECT s.student_id, s.first_name, s.last_name, c.course_name, g.grade,
         RANK() OVER (PARTITION BY g.course_id ORDER BY g.grade ASC) AS pos
  FROM grades g
  JOIN students s ON s.student_id = g.student_id
  JOIN courses  c ON c.course_id  = g.course_id
) AS ranked
WHERE pos = 1;

-- =====================================================================
-- STEP 9 · Alibis  -  CTE + crime window DERIVED from the data
-- Basic: 19:37 / 19:48 are typed in by hand.
-- Here the crime_window CTE reads them from the ghost badge swipe. No magic
-- numbers: if the data changed, the query would follow.
-- =====================================================================
WITH crime_window AS (
  SELECT a.access_date AS d, a.entry_time AS t_in, a.exit_time AS t_out
  FROM access_log a
  WHERE a.location = 'Room 204'
    AND NOT EXISTS (SELECT 1 FROM badges b WHERE b.badge_id = a.badge_id)
    AND a.access_date = '2026-09-21'
)
SELECT att.student_id, 'lecture' AS alibi
FROM attendance att
JOIN lectures l     ON l.lecture_id = att.lecture_id
JOIN crime_window w ON l.lecture_date = w.d
                   AND l.start_time <= w.t_in AND l.end_time >= w.t_out
UNION
SELECT b.student_id, a.location
FROM access_log a
JOIN badges b       ON b.badge_id = a.badge_id
JOIN crime_window w ON a.access_date = w.d
                   AND a.entry_time <= w.t_in AND a.exit_time >= w.t_out
WHERE a.location IN ('Library', 'Gym');

-- =====================================================================
-- STEP 10 · No alibi  -  CTE pipeline + ANTI-JOIN
-- Each CTE is one step of the investigation with a name:
-- crime_window -> inside -> alibi. A final LEFT JOIN ... IS NULL
-- (anti-join) removes everyone with an alibi. Same result as EXCEPT, but
-- with the students' names.
-- =====================================================================
WITH crime_window AS (
  SELECT a.access_date AS d, a.entry_time AS t_in, a.exit_time AS t_out
  FROM access_log a
  WHERE a.location = 'Room 204' AND a.access_date = '2026-09-21'
    AND NOT EXISTS (SELECT 1 FROM badges b WHERE b.badge_id = a.badge_id)
),
inside AS (
  SELECT b.student_id
  FROM access_log a
  JOIN badges b       ON b.badge_id = a.badge_id
  JOIN crime_window w ON a.access_date = w.d
                     AND a.entry_time <= w.t_in AND a.exit_time >= w.t_out
  WHERE a.location = 'Main Entrance'
),
alibi AS (
  SELECT att.student_id
  FROM attendance att
  JOIN lectures l     ON l.lecture_id = att.lecture_id
  JOIN crime_window w ON l.lecture_date = w.d
                     AND l.start_time <= w.t_in AND l.end_time >= w.t_out
  UNION
  SELECT b.student_id
  FROM access_log a
  JOIN badges b       ON b.badge_id = a.badge_id
  JOIN crime_window w ON a.access_date = w.d
                     AND a.entry_time <= w.t_in AND a.exit_time >= w.t_out
  WHERE a.location IN ('Library', 'Gym')
)
SELECT i.student_id, s.first_name, s.last_name
FROM inside i
JOIN students s ON s.student_id = i.student_id
LEFT JOIN alibi al ON al.student_id = i.student_id
WHERE al.student_id IS NULL;

-- =====================================================================
-- STEP 11 · Case closed  -  the WHOLE CASE SOLVED IN ONE QUERY
-- INSERT ... WITH ... SELECT: name, motive and time are not typed in, the
-- database computes them: window from the ghost badge, who was inside,
-- who has no alibi, who is an ex of Max's girlfriend. Even the motive text
-- is built with CONCAT from her name.
-- Note: at 10M rows this version is slow unless crime_window has LIMIT 1
-- (see benchmark/case_all_in_one_fixed.sql and the README).
-- =====================================================================
DROP TABLE IF EXISTS solution;
CREATE TABLE solution (
  first_name  VARCHAR(50),
  last_name   VARCHAR(50),
  motive      VARCHAR(200),
  murder_time TIME
);
INSERT INTO solution (first_name, last_name, motive, murder_time)
WITH crime_window AS (
  SELECT a.access_date AS d, a.entry_time AS t_in, a.exit_time AS t_out
  FROM access_log a
  WHERE a.location = 'Room 204' AND a.access_date = '2026-09-21'
    AND NOT EXISTS (SELECT 1 FROM badges b WHERE b.badge_id = a.badge_id)
),
inside AS (
  SELECT b.student_id
  FROM access_log a
  JOIN badges b       ON b.badge_id = a.badge_id
  JOIN crime_window w ON a.access_date = w.d
                     AND a.entry_time <= w.t_in AND a.exit_time >= w.t_out
  WHERE a.location = 'Main Entrance'
),
alibi AS (
  SELECT att.student_id
  FROM attendance att
  JOIN lectures l     ON l.lecture_id = att.lecture_id
  JOIN crime_window w ON l.lecture_date = w.d
                     AND l.start_time <= w.t_in AND l.end_time >= w.t_out
  UNION
  SELECT b.student_id
  FROM access_log a
  JOIN badges b       ON b.badge_id = a.badge_id
  JOIN crime_window w ON a.access_date = w.d
                     AND a.entry_time <= w.t_in AND a.exit_time >= w.t_out
  WHERE a.location IN ('Library', 'Gym')
),
jealous_exes AS (
  SELECT ex.student_id, girl.first_name AS her_name
  FROM relationships cur
  JOIN relationships ex ON ex.partner_id = cur.partner_id AND ex.end_date IS NOT NULL
  JOIN students girl    ON girl.student_id = cur.partner_id
  WHERE cur.student_id = 201 AND cur.end_date IS NULL
)
SELECT s.first_name, s.last_name,
       CONCAT('Love jealousy: ', j.her_name, ' left him for Maximilian') AS motive,
       w.t_in AS murder_time
FROM inside i
JOIN students s     ON s.student_id = i.student_id
JOIN jealous_exes j ON j.student_id = i.student_id
CROSS JOIN crime_window w
WHERE i.student_id NOT IN (SELECT student_id FROM alibi);
SELECT * FROM solution;

-- =====================================================================
-- BONUS 1 · Room 204 minute by minute  -  RECURSIVE CTE
-- WITH RECURSIVE generates the minutes from 19:30 to 20:05
-- (1170 = 19*60 + 30), then each minute lists who was in the room.
-- B-9147 appears at 19:37 and disappears at 19:48; Max stays.
-- =====================================================================
WITH RECURSIVE minutes AS (
  SELECT 1170 AS m
  UNION ALL
  SELECT m + 1 FROM minutes WHERE m < 1205
),
clock AS (
  SELECT CONCAT(CASE WHEN m >= 1200 THEN '20' ELSE '19' END, ':',
                CASE WHEN m % 60 < 10 THEN CONCAT('0', m % 60) ELSE CONCAT('', m % 60) END,
                ':00') AS t
  FROM minutes
)
SELECT c.t AS minute,
       GROUP_CONCAT(COALESCE(s.last_name, CONCAT('?? ', a.badge_id))) AS inside_room_204
FROM clock c
LEFT JOIN access_log a ON a.location = 'Room 204'
                      AND a.access_date = '2026-09-21'
                      AND a.entry_time <= c.t
                      AND (a.exit_time IS NULL OR a.exit_time >= c.t)
LEFT JOIN badges b   ON b.badge_id   = a.badge_id
LEFT JOIN students s ON s.student_id = b.student_id
GROUP BY c.t
ORDER BY c.t;

-- =====================================================================
-- BONUS 2 · Suspicion score for EVERY student  -  CASE + EXISTS
-- Each clue becomes a 0/1 column; the score weighs "inside with no alibi"
-- most (x3), then a romantic motive (x2), then knowing the room (x1).
-- Ranking: Tommaso 6, Beatrice 3 (she has an alibi), then the others.
-- =====================================================================
WITH evidence AS (
  SELECT s.student_id, s.first_name, s.last_name,
    CASE WHEN EXISTS (SELECT 1 FROM access_log a JOIN badges b ON b.badge_id = a.badge_id
                      WHERE b.student_id = s.student_id AND a.location = 'Main Entrance'
                        AND a.access_date = '2026-09-21'
                        AND a.entry_time <= '19:37:00' AND a.exit_time >= '19:48:00')
         THEN 1 ELSE 0 END AS in_building,
    CASE WHEN NOT EXISTS (SELECT 1 FROM attendance att JOIN lectures l ON l.lecture_id = att.lecture_id
                          WHERE att.student_id = s.student_id AND l.lecture_date = '2026-09-21'
                            AND l.start_time <= '19:37:00' AND l.end_time >= '19:48:00')
          AND NOT EXISTS (SELECT 1 FROM access_log a JOIN badges b ON b.badge_id = a.badge_id
                          WHERE b.student_id = s.student_id AND a.location IN ('Library','Gym')
                            AND a.access_date = '2026-09-21'
                            AND a.entry_time <= '19:37:00' AND a.exit_time >= '19:48:00')
         THEN 1 ELSE 0 END AS no_alibi,
    CASE WHEN EXISTS (SELECT 1 FROM relationships r
                      WHERE r.student_id = s.student_id AND r.end_date IS NOT NULL
                        AND r.partner_id IN (SELECT partner_id FROM relationships
                                             WHERE student_id = 201 AND end_date IS NULL))
           OR EXISTS (SELECT 1 FROM relationships r
                      WHERE r.student_id = s.student_id AND r.partner_id = 201)
         THEN 1 ELSE 0 END AS love_motive,
    CASE WHEN (SELECT COUNT(*) FROM access_log a JOIN badges b ON b.badge_id = a.badge_id
               WHERE b.student_id = s.student_id AND a.location = 'Room 204'
                 AND a.access_date BETWEEN '2026-09-14' AND '2026-09-20') > 3
         THEN 1 ELSE 0 END AS knows_room
  FROM students s
  WHERE s.student_id <> 201
)
SELECT student_id, first_name, last_name,
       in_building, no_alibi, love_motive, knows_room,
       3*in_building*no_alibi + 2*love_motive + knows_room AS suspicion_score
FROM evidence
ORDER BY suspicion_score DESC
LIMIT 5;
