-- A normal busy day on 2026-09-21 too (27,000 swipes), all of them finished
-- before 19:30, so the logic of the case is unchanged.
USE big_10m;
INSERT INTO access_log (access_id, badge_id, location, access_date, entry_time, exit_time)
SELECT 20000000 + n,
       CONCAT('X-', LPAD(CRC32(CONCAT('mbadge', n)) % 50000, 7, '0')),
       ELT(1 + CRC32(CONCAT('mloc', n)) % 4, 'Main Entrance', 'Library', 'Gym', 'Room 204'),
       '2026-09-21',
       SEC_TO_TIME(t_in),
       SEC_TO_TIME(LEAST(t_in + 300 + CRC32(CONCAT('mstay', n)) % 7200, 70200))
FROM (SELECT a.n * 10000 + b.n AS n,
             25200 + CRC32(CONCAT('min', a.n * 10000 + b.n)) % 36000 AS t_in
      FROM seq a JOIN seq b WHERE a.n < 3 AND a.n * 10000 + b.n < 27000) s;
