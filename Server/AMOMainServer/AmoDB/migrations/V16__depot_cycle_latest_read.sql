-- Bound the fleet snapshot lookup to one cycle per vehicle.
CREATE INDEX ix_demo_depot_cycle_latest ON demo_depot_cycles (vehicle_id, id DESC);
