"""Fit a bounded two-output ridge model for each prespecified forecast horizon."""

from dataclasses import dataclass
from statistics import mean

from .forecast_data import HORIZONS, Example, Outcome
from .trial import VEHICLE_COUNT


@dataclass(frozen=True)
class Predictor:
    """Linear predictor coefficients for vehicle count and waiting seconds."""

    queue: tuple[float, ...]
    waiting: tuple[float, ...]

    def predict(self, features: tuple[float, ...]) -> Outcome:
        """Predict bounded queue count and nonnegative seconds from a cutoff row."""
        vector = (1.0, *features)
        queue = sum(a * b for a, b in zip(self.queue, vector, strict=True))
        wait = sum(a * b for a, b in zip(self.waiting, vector, strict=True))
        bounded_queue = max(0.0, min(float(VEHICLE_COUNT), queue))
        bounded_wait = max(0.0, min(600.0, wait))
        return Outcome(bounded_queue, bounded_wait)


def _solve(matrix: list[list[float]]) -> tuple[tuple[float, ...], tuple[float, ...]]:
    dimensions = len(matrix)
    for column in range(dimensions):
        pivot = max(range(column, dimensions), key=lambda row: abs(matrix[row][column]))
        matrix[column], matrix[pivot] = matrix[pivot], matrix[column]
        value = matrix[column][column]
        matrix[column] = [entry / value for entry in matrix[column]]
        for row, entries in enumerate(matrix):
            if row != column:
                factor = entries[column]
                matrix[row] = [
                    a - factor * b for a, b in zip(entries, matrix[column], strict=True)
                ]
    return tuple(row[-2] for row in matrix), tuple(row[-1] for row in matrix)


def _fit(rows: list[Example]) -> Predictor:
    if not rows:
        raise ValueError('Each horizon must have training observations.')
    size = len(rows[0].features) + 1
    matrix = [[0.0] * (size + 2) for _ in range(size)]
    for row in rows:
        vector = (1.0, *row.features)
        outcome = (*vector, row.label.queue, row.label.wait_s)
        for i, weight in enumerate(vector):
            for j, actual in enumerate(outcome):
                matrix[i][j] += weight * actual
    for i in range(1, size):
        matrix[i][i] += 2.0
    queue, waiting = _solve(matrix)
    return Predictor(queue, waiting)


@dataclass(frozen=True)
class Evaluation:
    """Per-horizon held-out sample counts and mean absolute errors in original units."""

    horizon_s: int
    examples: int
    baseline_queue_mae: float
    model_queue_mae: float
    baseline_wait_mae_s: float
    model_wait_mae_s: float


def fit_and_evaluate(
    train: tuple[Example, ...], test: tuple[Example, ...]
) -> tuple[dict[int, Predictor], tuple[Evaluation, ...]]:
    """Fit and compare by horizon, rejecting any run present in both partitions."""
    if {row.seed for row in train}.intersection(row.seed for row in test):
        raise ValueError('Training and evaluation runs must be disjoint.')
    models = {}
    results = []
    for horizon in HORIZONS:
        model = _fit([row for row in train if row.horizon_s == horizon])
        models[horizon] = model
        pairs = [
            (row, model.predict(row.features))
            for row in test
            if row.horizon_s == horizon
        ]
        if not pairs:
            raise ValueError('Each horizon must have held-out observations.')
        results.append(
            Evaluation(
                horizon,
                len(pairs),
                mean(abs(r.label.queue - r.baseline.queue) for r, _ in pairs),
                mean(abs(r.label.queue - p.queue) for r, p in pairs),
                mean(abs(r.label.wait_s - r.baseline.wait_s) for r, _ in pairs),
                mean(abs(r.label.wait_s - p.wait_s) for r, p in pairs),
            )
        )
    return models, tuple(results)
