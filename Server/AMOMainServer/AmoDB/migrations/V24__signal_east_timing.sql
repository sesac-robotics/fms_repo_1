-- Separate east yellow and the partner board's east time (six-number PLAN), so the
-- two boards of a coordinated junction may give each east-west approach its own
-- green and yellow while still computing one cycle.
ALTER TABLE signal_latest ADD COLUMN east_yellow_ms integer;
UPDATE signal_latest SET east_yellow_ms = yellow_ms;
ALTER TABLE signal_latest ALTER COLUMN east_yellow_ms SET NOT NULL;
ALTER TABLE signal_latest ADD COLUMN partner_east_ms integer NOT NULL DEFAULT 0;
