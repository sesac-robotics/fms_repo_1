"""Write a Parquet training set and a versioned, read-only FMS replay artifact."""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid5

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]

from .forecast_data import FEATURE_NAMES, Example
from .regression import Evaluation, Predictor
from .road_graph import IMAGE_ANCHOR, INTERSECTION_ID, MAP_SHA256, MAP_VERSION
from .trial import TICKS_PER_SECOND, VEHICLE_COUNT


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8'
    )


def _row(
    experiment_id: UUID, split: Literal['train', 'test'], row: Example
) -> dict[str, object]:
    return {
        'run_id': str(uuid5(experiment_id, str(row.seed))),
        'seed': row.seed,
        'split': split,
        'tick': row.tick,
        'horizon_s': row.horizon_s,
        **dict(
            zip(FEATURE_NAMES, (float(value) for value in row.features), strict=True)
        ),
        'baseline_queue': row.baseline.queue,
        'baseline_wait_s': row.baseline.wait_s,
        'observed_queue': row.label.queue,
        'observed_wait_s': row.label.wait_s,
    }


def export(
    folder: Path,
    experiment_id: UUID,
    train: tuple[Example, ...],
    test: tuple[Example, ...],
    models: dict[int, Predictor],
    metrics: tuple[Evaluation, ...],
) -> None:
    """Write experiment data, held-out metrics and one held-out replay to a staging directory."""
    training = [_row(experiment_id, 'train', row) for row in train]
    testing = [_row(experiment_id, 'test', row) for row in test]
    pq.write_table(
        pa.Table.from_pylist(training + testing), folder / 'training.parquet'
    )
    _write_json(
        folder / 'report.json',
        {
            'experiment_id': str(experiment_id),
            'map_version': MAP_VERSION,
            'ticks_per_second': TICKS_PER_SECOND,
            'train_seeds': sorted({row.seed for row in train}),
            'test_seeds': sorted({row.seed for row in test}),
            'metrics': [asdict(value) for value in metrics],
            'features': FEATURE_NAMES,
            'models': {
                str(horizon): asdict(model) for horizon, model in models.items()
            },
        },
    )
    replay_seed = test[0].seed
    _write_json(
        folder / 'forecast.json',
        {
            'version': 1,
            'kind': 'synthetic-intersection-replay',
            'run_id': str(uuid5(experiment_id, str(replay_seed))),
            'seed': replay_seed,
            'map_sha256': MAP_SHA256,
            'intersection_id': INTERSECTION_ID,
            'image_anchor': IMAGE_ANCHOR,
            'vehicle_count': VEHICLE_COUNT,
            'ticks_per_second': TICKS_PER_SECOND,
            'forecasts': [
                {
                    'tick': row.tick,
                    'horizon_s': row.horizon_s,
                    'model': asdict(models[row.horizon_s].predict(row.features)),
                    'baseline': asdict(row.baseline),
                    'observed': asdict(row.label),
                }
                for row in test
                if row.seed == replay_seed
            ],
        },
    )
