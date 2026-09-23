-- =====================================================================
--  Murder at Viale Romania - the 11 steps of the browser game
--  Course techniques only. Paste one query at a time, Run, then Submit.
--  Works on the game's engine (SQLite) and on MySQL 8.
-- =====================================================================

-- STEP 1 · The report
SELECT *
FROM crime_reports
WHERE campus = 'Viale Romania'
ORDER BY report_date DESC, report_time DESC
LIMIT 1;
-- STEP 2 · Room 204
SELECT DISTINCT s.student_id, s.first_name, s.last_name
FROM access_log a
JOIN badges b   ON b.badge_id   = a.badge_id
JOIN students s ON s.student_id = b.student_id
WHERE a.location = 'Room 204'
  AND a.access_date = '2026-09-21';
-- STEP 3 · The ghost badge
SELECT a.*
FROM access_log a
LEFT JOIN badges b ON b.badge_id = a.badge_id
WHERE b.badge_id IS NULL
  AND a.location = 'Room 204'
  AND a.access_date = '2026-09-21';
-- STEP 4 · The regulars
SELECT s.student_id, s.first_name, s.last_name, COUNT(*) AS visits
FROM access_log a
JOIN badges b   ON b.badge_id   = a.badge_id
JOIN students s ON s.student_id = b.student_id
WHERE a.location = 'Room 204'
  AND a.access_date BETWEEN '2026-09-14' AND '2026-09-20'
GROUP BY s.student_id, s.first_name, s.last_name
HAVING COUNT(*) > 3
ORDER BY visits DESC;
-- STEP 5 · Her past
SELECT r.student_id, s.first_name, s.last_name, r.start_date, r.end_date
FROM relationships r
JOIN students s ON s.student_id = r.student_id
WHERE r.partner_id = (SELECT partner_id FROM relationships
                      WHERE student_id = 201 AND end_date IS NULL)
  AND r.end_date IS NOT NULL;
-- STEP 6 · Report cards
SELECT t.student_id, s.first_name, s.last_name, t.avg_grade
FROM (SELECT student_id, AVG(grade) AS avg_grade
      FROM grades
      GROUP BY student_id) AS t
JOIN students s ON s.student_id = t.student_id
WHERE t.avg_grade < 22;
-- STEP 7 · Points behind
SELECT g.student_id, g.grade,
       (SELECT grade FROM grades WHERE student_id = 201 AND course_id = 1) - g.grade AS points_behind
FROM grades g
WHERE g.course_id = 1
  AND g.student_id <> 201;
-- STEP 8 · Last in class
SELECT DISTINCT s.student_id, s.first_name, s.last_name
FROM grades g
JOIN students s ON s.student_id = g.student_id
WHERE g.grade = (SELECT MIN(g2.grade)
                 FROM grades g2
                 WHERE g2.course_id = g.course_id);
-- STEP 9 · Alibis
SELECT att.student_id, 'lecture' AS alibi
FROM attendance att
JOIN lectures l ON l.lecture_id = att.lecture_id
WHERE l.lecture_date = '2026-09-21'
  AND l.start_time <= '19:37:00' AND l.end_time >= '19:48:00'
UNION
SELECT b.student_id, a.location AS alibi
FROM access_log a
JOIN badges b ON b.badge_id = a.badge_id
WHERE a.access_date = '2026-09-21'
  AND a.location IN ('Library', 'Gym')
  AND a.entry_time <= '19:37:00' AND a.exit_time >= '19:48:00';
-- STEP 10 · No alibi
SELECT b.student_id
FROM access_log a
JOIN badges b ON b.badge_id = a.badge_id
WHERE a.location = 'Main Entrance' AND a.access_date = '2026-09-21'
  AND a.entry_time <= '19:37:00' AND a.exit_time >= '19:48:00'
EXCEPT
SELECT att.student_id
FROM attendance att
JOIN lectures l ON l.lecture_id = att.lecture_id
WHERE l.lecture_date = '2026-09-21'
  AND l.start_time <= '19:37:00' AND l.end_time >= '19:48:00'
EXCEPT
SELECT b.student_id
FROM access_log a
JOIN badges b ON b.badge_id = a.badge_id
WHERE a.access_date = '2026-09-21'
  AND a.location IN ('Library', 'Gym')
  AND a.entry_time <= '19:37:00' AND a.exit_time >= '19:48:00';

-- STEP 11 · Case closed  (Run, then "Check solution")
CREATE TABLE solution (
  first_name  VARCHAR(50),
  last_name   VARCHAR(50),
  motive      VARCHAR(200),
  murder_time TIME
);
INSERT INTO solution VALUES
  ('Tommaso', 'Arcuri', 'Love jealousy: Ginevra left him for Maximilian', '19:37:00');
