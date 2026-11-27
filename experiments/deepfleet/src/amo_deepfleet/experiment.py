"""Orchestrate independently seeded runs and compare predictions on held-out runs."""

from dataclasses import dataclass
from itertools import chain

from .forecast_data import Example, examples
from .regression import Evaluation, Predictor, fit_and_evaluate
from .simulation import simulate
from .trial import Trial


@dataclass(frozen=True)
class Experiment:
    """Run-level partition, forecast examples and model evidence without external resources."""

    partitions: tuple[tuple[str, Trial], ...]
    train: tuple[Example, ...]
    test: tuple[Example, ...]
    models: dict[int, Predictor]
    metrics: tuple[Evaluation, ...]


def run_experiment(
    seed: int, duration_s: int, train_count: int, test_count: int
) -> Experiment:
    """Fit and evaluate 3–30 runs per partition with non-overlapping 31-bit seeds."""
    if not 3 <= train_count <= 30 or not 3 <= test_count <= 30:
        raise ValueError('Each partition requires 3–30 independently seeded runs.')
    if not 0 <= seed <= 2**31 - train_count - test_count:
        raise ValueError('Run seeds must remain within the nonnegative 31-bit range.')
    trials = tuple(
        simulate(seed + index, duration_s) for index in range(train_count + test_count)
    )
    train = tuple(
        chain.from_iterable(examples(trial) for trial in trials[:train_count])
    )
    test = tuple(chain.from_iterable(examples(trial) for trial in trials[train_count:]))
    models, metrics = fit_and_evaluate(train, test)
    partitions = tuple(
        ('train' if index < train_count else 'test', trial)
        for index, trial in enumerate(trials)
    )
    return Experiment(partitions, train, test, models, metrics)
