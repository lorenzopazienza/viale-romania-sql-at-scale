USE big_10m;
-- a normal busy day on 21/09 too (~27k swipes), all finished before 19:30 so the case logic is unchanged
INSERT INTO access_log (access_id, badge_id, location, access_date, entry_time, exit_time)
SELECT 20000000 + n,
       CONCAT('X-', LPAD(FLOOR(RAND(n+11)*50000), 7, '0')),
       ELT(1 + FLOOR(RAND(n+12)*4), 'Main Entrance', 'Library', 'Gym', 'Room 204'),
       '2026-09-21',
       SEC_TO_TIME(t_in),
       SEC_TO_TIME(LEAST(t_in + 300 + FLOOR(RAND(n+14)*7200), 70200))
FROM (SELECT a.n*10000 + b.n AS n, 25200 + FLOOR(RAND(a.n*10000+b.n+13)*36000) AS t_in
      FROM seq a JOIN seq b WHERE a.n < 3 AND a.n*10000+b.n < 27000) s;
