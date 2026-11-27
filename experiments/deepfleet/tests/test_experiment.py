"""Test repeatability, admission safety and train/test separation in the pilot."""

import json
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path
from uuid import uuid4

import pyarrow.parquet as pq  # type: ignore[import-untyped]

from amo_deepfleet.artifacts import export
from amo_deepfleet.experiment import run_experiment
from amo_deepfleet.forecast_data import HORIZONS, examples
from amo_deepfleet.log_rows import motions, signals, telemetry
from amo_deepfleet.regression import fit_and_evaluate
from amo_deepfleet.simulation import simulate
from amo_deepfleet.trial import Motion, Phase


class SimulationTest(unittest.TestCase):
    """Check controlled repeatability and crossing behavior at simulation boundaries."""

    def test_reproducible_four_vehicle_frames_and_full_exit(self) -> None:
        trial = simulate(2720, 90)
        self.assertEqual(trial, simulate(2720, 90))
        self.assertNotEqual(trial.frames, simulate(2723, 90).frames)
        self.assertEqual(len(trial.frames), 900)
        self.assertTrue(any(frame.exit_closed for frame in trial.frames))
        self.assertTrue(
            any(
                sample.wait_reason for frame in trial.frames for sample in frame.samples
            )
        )
        self.assertGreater(len(trial.passages), 4)
        for frame in trial.frames:
            self.assertEqual(
                {sample.vehicle_id for sample in frame.samples}, {1, 2, 3, 4}
            )
            self.assertTrue(all(0 <= sample.progress <= 1 for sample in frame.samples))
            self.assertLessEqual(
                sum(sample.motion == Motion.CROSSING for sample in frame.samples), 1
            )
        grants = [p for p in trial.passages if p.grant_tick is not None]
        grants.sort(key=lambda p: p.grant_tick if p.grant_tick is not None else -1)
        for index, grant in enumerate(grants):
            assert grant.grant_tick is not None
            frame = trial.frames[grant.grant_tick]
            self.assertFalse(frame.exit_closed)
            self.assertEqual(frame.phase, Phase(f'{grant.approach.value}_GREEN'))
            self.assertEqual(grant.entry_tick, grant.grant_tick)
            eligible = [
                (p.request_tick, p.vehicle_id)
                for p in trial.passages
                if p.approach == grant.approach
                and p.request_tick <= grant.grant_tick
                and (p.grant_tick is None or p.grant_tick >= grant.grant_tick)
            ]
            self.assertEqual((grant.request_tick, grant.vehicle_id), min(eligible))
            if index:
                full_exit = grants[index - 1].exit_tick
                assert full_exit is not None
                self.assertLessEqual(full_exit, grant.grant_tick)

    def test_intervals_cover_the_whole_run(self) -> None:
        trial, run = simulate(2721, 60), uuid4()
        self.assertEqual(sum(1 for _ in telemetry(run, trial)), 600 * 4)
        per_car: dict[object, list[tuple[object, object]]] = defaultdict(list)
        for record in motions(run, trial):
            per_car[record[2]].append((record[3], record[4]))
        for intervals in per_car.values():
            self.assertEqual(intervals[0][0], 0)
            self.assertEqual(intervals[-1][1], 600)
            self.assertEqual(
                [right for _, right in intervals[:-1]],
                [left for left, _ in intervals[1:]],
            )
        phases = list(signals(run, trial))
        self.assertEqual(phases[0][1], 0)
        self.assertEqual(phases[-1][2], 600)


class ExperimentTest(unittest.TestCase):
    """Check labels, run-level split and portable results."""

    def test_uses_observed_future_only_for_labels(self) -> None:
        trial = simulate(2720, 90)
        rows = examples(trial)
        self.assertTrue(rows)
        for row in rows:
            future = trial.frames[row.tick + row.horizon_s * 10]
            self.assertEqual(
                row.label.queue, sum(s.motion == Motion.WAITING for s in future.samples)
            )
        with self.assertRaisesRegex(ValueError, 'disjoint'):
            fit_and_evaluate(rows, rows)

    def test_parquet_and_replay_share_held_out_identifiers(self) -> None:
        study = run_experiment(2718, 60, 3, 3)
        self.assertEqual(set(study.models), set(HORIZONS))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            export(root, uuid4(), study.train, study.test, study.models, study.metrics)
            report = json.loads((root / 'report.json').read_text())
            forecast = json.loads((root / 'forecast.json').read_text())
            records = pq.read_table(root / 'training.parquet').to_pylist()
            self.assertEqual(len(records), len(study.train) + len(study.test))
            self.assertEqual(set(report['train_seeds']), {2718, 2719, 2720})
            self.assertEqual(set(report['test_seeds']), {2721, 2722, 2723})
            matching = [row for row in records if row['run_id'] == forecast['run_id']]
            self.assertTrue(matching)
            self.assertTrue(all(row['split'] == 'test' for row in matching))
            self.assertEqual(len(matching), len(forecast['forecasts']))
