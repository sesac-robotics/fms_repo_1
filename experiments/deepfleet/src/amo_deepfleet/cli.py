"""Command line for the offline experiment and its explicitly selected PostgreSQL store."""

import argparse
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import psycopg

from .artifacts import export
from .experiment import Experiment, run_experiment
from .postgres import store_experiment


def _publish(output: Path, study: Experiment, dsn: str | None) -> None:
    output.mkdir()
    published = []
    experiment_id = uuid4()
    try:
        with TemporaryDirectory(dir=output.parent) as temporary:
            stage = Path(temporary)
            export(
                stage,
                experiment_id,
                study.train,
                study.test,
                study.models,
                study.metrics,
            )
            if dsn:
                store_experiment(dsn, experiment_id, study.partitions)
            for name in ('training.parquet', 'report.json', 'forecast.json'):
                published.append((stage / name).rename(output / name))
    except BaseException:
        for path in published:
            path.unlink()
        output.rmdir()
        raise


def main() -> int:
    """Parse CLI arguments, publish outputs, and print held-out MAE by horizon."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--output', required=True, type=Path, help='New output directory'
    )
    parser.add_argument('--seed', type=int, default=2718)
    parser.add_argument(
        '--duration', type=int, default=180, help='Seconds per simulated run'
    )
    parser.add_argument('--train-runs', type=int, default=12)
    parser.add_argument('--test-runs', type=int, default=6)
    parser.add_argument(
        '--postgres',
        action='store_true',
        help='Store raw runs at the explicitly configured AMO_LEARNING_DSN',
    )
    args = parser.parse_args()
    dsn = os.environ.get('AMO_LEARNING_DSN') if args.postgres else None
    if args.postgres and not dsn:
        parser.error(
            'Set AMO_LEARNING_DSN to the intended experiment PostgreSQL endpoint.'
        )
    try:
        if args.output.exists() or args.output.is_symlink():
            raise FileExistsError('The experiment output path must be new.')
        trial = run_experiment(
            args.seed, args.duration, args.train_runs, args.test_runs
        )
        _publish(args.output, trial, dsn)
    except (ValueError, OSError) as error:
        parser.exit(1, f'{error}\n')
    except psycopg.Error as error:
        state = error.sqlstate or type(error).__name__
        parser.exit(1, f'Experiment PostgreSQL write failed ({state}).\n')
    for row in trial.metrics:
        print(
            f'{row.horizon_s}s ({row.examples}): queue MAE '
            f'{row.baseline_queue_mae:.3f} baseline / {row.model_queue_mae:.3f} model, '
            f'wait MAE {row.baseline_wait_mae_s:.3f}s baseline / {row.model_wait_mae_s:.3f}s model'
        )
    print(args.output)
    return 0
