-- Copy table definitions only. Existing public records remain historical evidence.
CREATE SCHEMA amo_review;
CREATE SEQUENCE amo_review.amo_record_id START WITH 2000000000;
CREATE TABLE amo_review.users (LIKE public.users INCLUDING ALL);
CREATE TABLE amo_review.vehicles (LIKE public.vehicles INCLUDING ALL);
CREATE TABLE amo_review.map_versions (LIKE public.map_versions INCLUDING ALL);
CREATE TABLE amo_review.places (LIKE public.places INCLUDING ALL);
CREATE TABLE amo_review.service_requests (LIKE public.service_requests INCLUDING ALL);
CREATE TABLE amo_review.dispatches (LIKE public.dispatches INCLUDING ALL);
CREATE TABLE amo_review.trips (LIKE public.trips INCLUDING ALL);
CREATE TABLE amo_review.route_revisions (LIKE public.route_revisions INCLUDING ALL);
CREATE TABLE amo_review.vehicle_commands (LIKE public.vehicle_commands INCLUDING ALL);
CREATE TABLE amo_review.operation_events (LIKE public.operation_events INCLUDING ALL);
CREATE TABLE amo_review.telemetry_samples (LIKE public.telemetry_samples INCLUDING ALL);
CREATE TABLE amo_review.facility_uses (LIKE public.facility_uses INCLUDING ALL);
CREATE TABLE amo_review.passenger_checks (LIKE public.passenger_checks INCLUDING ALL);
CREATE TABLE amo_review.ride_fare_quotes (LIKE public.ride_fare_quotes INCLUDING ALL);
CREATE TABLE amo_review.ride_payment_attempts (LIKE public.ride_payment_attempts INCLUDING ALL);
CREATE TABLE amo_review.ride_fare_settlements (LIKE public.ride_fare_settlements INCLUDING ALL);
CREATE TABLE amo_review.ride_route_changes (LIKE public.ride_route_changes INCLUDING ALL);
CREATE TABLE amo_review.demo_depot_cycles (LIKE public.demo_depot_cycles INCLUDING ALL);
CREATE TABLE amo_review.demo_scenario_runs (LIKE public.demo_scenario_runs INCLUDING ALL);
CREATE TABLE amo_review.demo_scenario_steps (LIKE public.demo_scenario_steps INCLUDING ALL);
CREATE TABLE amo_review.demo_scenario_current (LIKE public.demo_scenario_current INCLUDING ALL);

ALTER TABLE amo_review.demo_scenario_runs ADD COLUMN closed_at timestamptz;

-- LIKE copies checks and unique indexes, but foreign keys must target the isolated tables.
-- Exclude the owner account reference so a review never needs to modify or lock user accounts.
SET LOCAL search_path TO amo_review, pg_catalog;
DO $review_constraints$
DECLARE
    relation record;
BEGIN
    FOR relation IN
        SELECT source.relname AS table_name, c.conname AS constraint_name,
               pg_get_constraintdef(c.oid) AS definition
        FROM pg_constraint c
        JOIN pg_class source ON source.oid = c.conrelid
        JOIN pg_class target ON target.oid = c.confrelid
        WHERE c.contype = 'f'
          AND source.relnamespace = 'public'::regnamespace
          AND target.relnamespace = 'public'::regnamespace
          AND to_regclass(format('amo_review.%I', source.relname)) IS NOT NULL
          AND to_regclass(format('amo_review.%I', target.relname)) IS NOT NULL
    LOOP
        EXECUTE format(
            'ALTER TABLE amo_review.%I ADD CONSTRAINT %I %s',
            relation.table_name, relation.constraint_name,
            replace(relation.definition, 'REFERENCES public.', 'REFERENCES amo_review.'));
    END LOOP;
END
$review_constraints$;
SET LOCAL search_path TO public, pg_catalog;

INSERT INTO amo_review.users (id, name, contact, mock_payment_method_ref, registered_at)
VALUES (1, 'Scenario Passenger', 'passenger@amo.test', 'demo-approved', statement_timestamp());
INSERT INTO amo_review.map_versions
SELECT * FROM public.map_versions WHERE version_key = 'v0.2';
INSERT INTO amo_review.places
SELECT p.* FROM public.places p JOIN amo_review.map_versions m ON m.id = p.map_version_id
WHERE p.place_key IN ('S1', 'S2', 'S3', 'S4');
INSERT INTO amo_review.demo_scenario_current (singleton) VALUES (true);

-- Historic synthetic vehicles are no longer eligible for the ordinary fleet view.
UPDATE public.vehicles SET scenario_visible = false
WHERE id IN (SELECT vehicle_id FROM public.demo_scenario_runs);
