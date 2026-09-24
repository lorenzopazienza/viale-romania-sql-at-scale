-- Run on a copy of luiss_mystery.
-- A reader should still record unknown cards (they are evidence),
-- but the database should raise an alert the moment one is swiped.
CREATE TABLE security_alerts (
  alert_id   INT AUTO_INCREMENT PRIMARY KEY,
  access_id  INT,
  badge_id   VARCHAR(10),
  location   VARCHAR(30),
  alert_at   DATETIME,
  reason     VARCHAR(100)
);

DELIMITER //
CREATE TRIGGER trg_unknown_badge
AFTER INSERT ON access_log
FOR EACH ROW
BEGIN
  IF NOT EXISTS (SELECT 1 FROM badges WHERE badge_id = NEW.badge_id) THEN
    INSERT INTO security_alerts (access_id, badge_id, location, alert_at, reason)
    VALUES (NEW.access_id, NEW.badge_id, NEW.location,
            TIMESTAMP(NEW.access_date, NEW.entry_time), 'UNKNOWN BADGE');
  END IF;
END//
DELIMITER ;

-- Replay the killer's swipe
DELETE FROM access_log WHERE access_id = 484;
INSERT INTO access_log VALUES (484, 'B-9147', 'Room 204', '2026-09-21', '19:37:00', '19:48:00');
SELECT * FROM security_alerts;   -- B-9147 | Room 204 | 2026-09-21 19:37:00 | UNKNOWN BADGE
