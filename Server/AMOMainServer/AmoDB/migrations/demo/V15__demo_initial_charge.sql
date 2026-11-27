-- A dedicated synthetic bay and initial charge cycle for the replay vehicle.
INSERT INTO places (id, map_version_id, place_key, name, kind, x_m, y_m)
SELECT nextval('amo_record_id'), id, 'DEMO-CHARGE-01', 'Demo charge bay', 'CHARGING_BAY', 0, 0
FROM map_versions WHERE version_key = 'v0.2';

INSERT INTO demo_depot_cycles (vehicle_id, place_id, phase)
SELECT v.id, p.id, 'INITIAL' FROM vehicles v CROSS JOIN places p
WHERE v.vehicle_no = 'DEMO-REPLAY-01' AND p.place_key = 'DEMO-CHARGE-01';
