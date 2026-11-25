-- Keep original run, evidence, and vehicle references readable after migration.
ALTER TABLE demo_scenario_runs DROP CONSTRAINT demo_scenario_runs_vehicle_id_key;

CREATE TABLE demo_scenario_current (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    run_id uuid REFERENCES demo_scenario_runs(id)
);

INSERT INTO demo_scenario_current (run_id)
VALUES ((SELECT id FROM demo_scenario_runs WHERE vehicle_id IS NOT NULL
         ORDER BY created_at DESC, id DESC LIMIT 1));

UPDATE vehicles SET scenario_visible = false
WHERE id IN (SELECT vehicle_id FROM demo_scenario_runs);

UPDATE vehicles v SET scenario_visible = true, scenario_run_id = r.id
FROM demo_scenario_current c JOIN demo_scenario_runs r ON r.id = c.run_id
WHERE v.id = r.vehicle_id;


DROP INDEX ux_demo_initial_depot_cycle;
CREATE UNIQUE INDEX ux_demo_initial_depot_cycle ON demo_depot_cycles (vehicle_id)
    WHERE dispatch_id IS NULL AND NOT scenario_archived;

DROP INDEX ux_demo_open_depot_cycle;
CREATE UNIQUE INDEX ux_demo_open_depot_cycle ON demo_depot_cycles (vehicle_id)
    WHERE phase <> 'VACATED' AND NOT scenario_archived;
