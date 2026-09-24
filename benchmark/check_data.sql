-- Sanity checks on the synthetic campus (run after generation).
USE big_10m;
SELECT COUNT(*) AS swipes, COUNT(DISTINCT badge_id) AS distinct_badges FROM access_log;
SELECT COUNT(*) AS days, MIN(c) AS min_swipes_per_day, MAX(c) AS max_swipes_per_day
FROM (SELECT access_date, COUNT(*) c FROM access_log GROUP BY access_date) t;
SELECT MIN(n_loc) AS min_locations_per_day, MIN(n_badges) AS min_badges_per_day
FROM (SELECT access_date, COUNT(DISTINCT location) n_loc, COUNT(DISTINCT badge_id) n_badges
      FROM access_log GROUP BY access_date) t;
SELECT location, COUNT(*) AS swipes FROM access_log GROUP BY location ORDER BY location;
SELECT COUNT(*) AS ghost_swipes, COUNT(DISTINCT a.badge_id) AS ghost_cards
FROM access_log a WHERE NOT EXISTS (SELECT 1 FROM badges b WHERE b.badge_id = a.badge_id);
SELECT location, COUNT(*) AS swipes_on_murder_day FROM access_log
WHERE access_date = '2026-09-21' GROUP BY location ORDER BY location;
