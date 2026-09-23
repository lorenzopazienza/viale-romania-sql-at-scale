WITH crime_window AS (
  SELECT a.access_date AS d, a.entry_time AS t_in, a.exit_time AS t_out
  FROM access_log a
  WHERE a.location = 'Room 204' AND a.access_date = '2026-09-21'
    AND NOT EXISTS (SELECT 1 FROM badges b WHERE b.badge_id = a.badge_id)
  LIMIT 1
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
WHERE i.student_id NOT IN (SELECT student_id FROM alibi)