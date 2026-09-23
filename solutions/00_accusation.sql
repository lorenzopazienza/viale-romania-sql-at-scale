-- =====================================================================
--  Murder at Viale Romania - the accusation (MySQL 8 / TablePlus)
--  Run after DEMO_luiss_mystery.sql
-- =====================================================================
--
--  WHO   : Tommaso Arcuri, student_id 203 (Global Data Lab)
--  HOW   : unregistered badge B-9147, Room 204, 21/09/2026,
--          in at 19:37:00, out at 19:48:00. The bang is heard at ~19:40.
--          Tommaso is in the building from 18:40:07 to 20:05:58
--          (Main Entrance) and is the only person inside for those
--          11 minutes without an alibi.
--  WHY   : jealousy. Ginevra Loreti (202) leaves Tommaso on 30/07/2026
--          and starts dating Maximilian on 20/08/2026 (still together).
--          At 18:45 Max is heard on the phone: "She chose me. Get over it."
--  PROOF : query 3 (ghost badge), query 5 (only suspect without an alibi),
--          query 6 (motive).
-- =====================================================================

USE luiss_mystery;

-- ---------------------------------------------------------------------
-- 1. The case file
-- ---------------------------------------------------------------------
SELECT *
FROM crime_reports
WHERE crime_type = 'murder';

-- ---------------------------------------------------------------------
-- 2. Witnesses for report 8 -> the times to check:
--    18:45 Max on the phone ("She chose me. Get over it.")
--    ~19:40 a bang from Room 204, then someone with a hood walks past
--    ~20:00 a guy in a grey Luiss hoodie leaves the building in a hurry
-- ---------------------------------------------------------------------
SELECT w.statement_id, s.student_id, s.first_name, s.last_name, w.statement
FROM witness_statements AS w
JOIN students AS s ON s.student_id = w.student_id
WHERE w.report_id = 8;

-- ---------------------------------------------------------------------
-- 3. Room 204 timeline on the day (LEFT JOIN keeps badges with no owner)
--    -> Max enters at 18:55:47 and never leaves (exit_time NULL)
--    -> B-9147 enters at 19:37 and leaves at 19:48: it belongs to nobody
-- ---------------------------------------------------------------------
SELECT a.access_id, a.badge_id, a.entry_time, a.exit_time,
       s.student_id, s.first_name, s.last_name
FROM access_log AS a
LEFT JOIN badges   AS b ON b.badge_id   = a.badge_id
LEFT JOIN students AS s ON s.student_id = b.student_id
WHERE a.access_date = '2026-09-21'
  AND a.location    = 'Room 204'
ORDER BY a.entry_time;

-- 4. Every swipe whose badge belongs to nobody
--    (B-0000 in the gym on 16/09 is noise; B-9147 is the one that matters)
SELECT a.*
FROM access_log AS a
WHERE NOT EXISTS (SELECT 1 FROM badges AS b WHERE b.badge_id = a.badge_id);

-- ---------------------------------------------------------------------
-- 5. Who was inside the building for the whole 19:37-19:48 window
--    and has NO alibi (no lecture, not in the Library or the Gym)?
--    -> one row: Tommaso Arcuri, 18:40:07 - 20:05:58
--    (Simone Colombo leaves at 19:45, before B-9147 leaves the room;
--     Anna D'Angelo arrives at 19:40, after it; Beatrice Solari is in the
--     Databases lecture 18:30-20:30; everyone else is in the Library or Gym.)
-- ---------------------------------------------------------------------
SELECT s.student_id, s.first_name, s.last_name, s.program,
       a.entry_time, a.exit_time
FROM access_log AS a
JOIN badges   AS b ON b.badge_id   = a.badge_id
JOIN students AS s ON s.student_id = b.student_id
WHERE a.access_date = '2026-09-21'
  AND a.location    = 'Main Entrance'
  AND a.entry_time <= '19:37:00'
  AND (a.exit_time >= '19:48:00' OR a.exit_time IS NULL)
  AND s.student_id <> 201                       -- the victim
  AND NOT EXISTS (                              -- alibi: in a lecture
        SELECT 1
        FROM attendance AS att
        JOIN lectures   AS l ON l.lecture_id = att.lecture_id
        WHERE att.student_id  = s.student_id
          AND l.lecture_date  = '2026-09-21'
          AND l.start_time   <= '19:37:00'
          AND l.end_time     >= '19:48:00')
  AND NOT EXISTS (                              -- alibi: Library or Gym
        SELECT 1
        FROM access_log AS a2
        JOIN badges     AS b2 ON b2.badge_id = a2.badge_id
        WHERE b2.student_id  = s.student_id
          AND a2.access_date = '2026-09-21'
          AND a2.location IN ('Library', 'Gym')
          AND a2.entry_time <= '19:37:00'
          AND a2.exit_time  >= '19:48:00');

-- ---------------------------------------------------------------------
-- 6. The motive: Ginevra Loreti's (202) relationship history
--    Tommaso    14/02/2024 -> 30/07/2026 (ended)
--    Maximilian 20/08/2026 -> NULL (still together)
-- ---------------------------------------------------------------------
SELECT r.relationship_id,
       s1.first_name AS person,  s1.last_name AS person_last,
       s2.first_name AS partner, s2.last_name AS partner_last,
       r.start_date, r.end_date
FROM relationships AS r
JOIN students AS s1 ON s1.student_id = r.student_id
JOIN students AS s2 ON s2.student_id = r.partner_id
WHERE r.student_id = 202
ORDER BY r.start_date;

-- ---------------------------------------------------------------------
-- 7. Supporting evidence: that night Tommaso never swipes his OWN badge
--    inside the building (Main Entrance only), although in the days
--    before he used Room 204 regularly with badge B-0203.
-- ---------------------------------------------------------------------
SELECT a.access_date, a.location, a.entry_time, a.exit_time
FROM access_log AS a
WHERE a.badge_id = 'B-0203'
ORDER BY a.access_date, a.entry_time;
