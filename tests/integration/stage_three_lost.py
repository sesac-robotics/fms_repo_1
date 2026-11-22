"""Test-only SD-12 metadata, mock Vision results, and notification ledger."""

from dataclasses import dataclass, field
from enum import Enum

from stage_two_vehicle import Scope


class Finding(Enum):
    """The three IF-09 results modeled without consuming photographs."""

    CANDIDATE = 'candidate'
    NONE = 'not_detected'
    UNAVAILABLE = 'comparison_unavailable'


class Recipient(Enum):
    """The two independent, authorized notification destinations."""

    RIDER = 'rider'
    ADMIN = 'admin'


@dataclass(frozen=True)
class Snapshot:
    """An opaque synthetic snapshot ID with its source and capture tick."""

    scope: Scope
    key: str
    captured: int


@dataclass(frozen=True)
class Detection:
    """Fixture data corresponding to part of an IF-09 report."""

    scope: Scope
    key: str
    observed: int
    finding: Finding
    before: Snapshot | None
    after: Snapshot | None


@dataclass
class Report:
    """Track attempts and first successes independently for each destination."""

    input: Detection
    finding: Finding
    success_at: dict[Recipient, int] = field(default_factory=dict, init=False)
    attempts: list[tuple[Recipient, int, bool]] = field(
        default_factory=list, init=False
    )
    corrections: list[tuple[int, str]] = field(default_factory=list, init=False)

    @property
    def latest_tick(self) -> int:
        """Expose the maximum accepted evidence tick for replay ordering."""
        return max(
            [
                self.input.observed,
                *(tick for _, tick, _ in self.attempts),
                *(tick for tick, _ in self.corrections),
            ]
        )


@dataclass
class LostProperty:
    """Bind reports to an alighted ride and its registered notification targets."""

    scope: Scope
    rider: str
    operator: str
    alighted_at: int
    _reports: dict[str, Report] = field(default_factory=dict, init=False)

    def accept(self, data: Detection) -> Report | None:
        """Reuse the same report only for an exact duplicate in this ride."""
        if data.scope != self.scope or not data.key or data.observed < self.alighted_at:
            return None
        previous = self._reports.get(data.key)
        if previous is not None:
            return previous if previous.input == data else None
        outcome = data.finding if self._paired(data) else Finding.UNAVAILABLE
        result = Report(data, outcome)
        self._reports[data.key] = result
        return result

    def _paired(self, data: Detection) -> bool:
        before, after = data.before, data.after
        return bool(
            before
            and after
            and before.scope == after.scope == self.scope
            and before.key
            and after.key
            and before.key != after.key
            and 0
            <= before.captured
            < self.alighted_at
            < after.captured
            <= data.observed
        )

    def pending(self, key: str) -> dict[Recipient, str]:
        """Project only unsent recipients for the current uncorrected candidate."""
        report = self._reports.get(key)
        if (
            report is None
            or report.finding is not Finding.CANDIDATE
            or report.corrections
        ):
            return {}
        targets = {Recipient.RIDER: self.rider, Recipient.ADMIN: self.operator}
        return {
            role: target
            for role, target in targets.items()
            if role not in report.success_at
        }

    def record_delivery(
        self, key: str, role: Recipient, target: str, tick: int, *, success: bool
    ) -> bool:
        """Keep a retry scoped to an unsent destination and its original case."""
        report = self._reports.get(key)
        if report is None or self.pending(key).get(role) != target:
            return False
        attempt = role, tick, success
        prior_tick = max((t for r, t, _ in report.attempts if r is role), default=-1)
        if tick < report.input.observed or tick <= prior_tick:
            return False
        report.attempts.append(attempt)
        if success:
            report.success_at[role] = tick
        return True

    def correct(self, key: str, operator: str, tick: int, reason: str) -> bool:
        """Log a synthetic false-positive correction and suppress pending retries."""
        report = self._reports.get(key)
        if (
            report is None
            or report.finding is not Finding.CANDIDATE
            or report.corrections
            or operator != self.operator
            or not reason.strip()
            or tick < report.latest_tick
        ):
            return False
        report.corrections.append((tick, reason))
        return True
