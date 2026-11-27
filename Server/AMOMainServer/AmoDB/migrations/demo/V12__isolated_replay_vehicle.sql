-- The replay vehicle is deliberately excluded from physical dispatch.
INSERT INTO vehicles (id, vehicle_no, dispatch_enabled, updated_at)
VALUES (nextval('amo_record_id'), 'DEMO-REPLAY-01', false, statement_timestamp());
