-- Run on a copy of luiss_mystery.
-- Try to enforce referential integrity on the badge readers' log.
-- Fails with ERROR 1452: orphan swipes (B-0000, B-9147) already exist.
ALTER TABLE access_log
  ADD CONSTRAINT fk_access_badge FOREIGN KEY (badge_id) REFERENCES badges(badge_id);
