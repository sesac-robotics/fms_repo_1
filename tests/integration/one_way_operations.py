"""Deterministic fixtures for SD-04 qualification and SD-06 command boundaries."""

from dataclasses import dataclass, field
from enum import Enum


@dataclass(frozen=True)
class PoseSample:
    """Mock localization result in metres/radians, keyed to an observation tick."""

    vehicle: str
    tick: int
    x_m: float
    y_m: float
    yaw_rad: float


@dataclass
class OperationsView:
    """Logical view fixture using pre-masked asset markers and supplied observations."""

    samples: dict[str, PoseSample] = field(default_factory=dict)

    def ingest(self, sample: PoseSample) -> bool:
        """Keep one freshest sample for each of the synthetic vehicles."""
        previous = self.samples.get(sample.vehicle)
        if previous is not None and sample.tick <= previous.tick:
            return False
        self.samples[sample.vehicle] = sample
        return True

    def same_tick(self, tick: int) -> dict[str, PoseSample]:
        """Return independent observations with the requested synthetic tick."""
        return {vehicle: s for vehicle, s in self.samples.items() if s.tick == tick}

    @staticmethod
    def display_asset(asset: str, *, fixture_is_masked: bool) -> str | None:
        """Select the marked fixture asset for display when masking is present."""
        return asset if fixture_is_masked else None


@dataclass
class Intersection:
    """First-arrived eligibility and exclusive occupancy on one synthetic crossing."""

    waiters: dict[str, int] = field(default_factory=dict)
    owner: str | None = None

    def queue(self, vehicle: str, at: int) -> None:
        """Record the first arrival of a vehicle at the stop line."""
        self.waiters.setdefault(vehicle, at)

    def admit(self, *, green: bool, empty: bool, exit_clear: bool) -> str | None:
        """Admit the earliest waiting vehicle when all three checks pass."""
        if self.owner is not None or not self.waiters:
            return None
        if not (green and empty and exit_clear):
            return None
        self.owner = min(self.waiters, key=lambda v: (self.waiters[v], v))
        del self.waiters[self.owner]
        return self.owner

    def release(self, vehicle: str, *, fully_exited: bool) -> bool:
        """Give up occupancy only on the current owner's complete exit report."""
        if self.owner != vehicle or not fully_exited:
            return False
        self.owner = None
        return True


@dataclass
class Routes:
    """Fixture routes ordered by preference, with a reversible segment block."""

    options: tuple[tuple[str, ...], ...]
    blocked: set[str] = field(default_factory=set)

    def current(self) -> tuple[str, ...] | None:
        """Select the first route without a blocked segment, or wait."""
        return next(
            (route for route in self.options if self.blocked.isdisjoint(route)),
            None,
        )


class CommandResult(Enum):
    """Four reported command outcomes, independent of physical state."""

    RECEIVED = 'received'
    REJECTED = 'rejected'
    COMPLETED = 'completed'
    FAILED = 'failed'


@dataclass
class Vehicle:
    """Synthetic vehicle and controller commands scoped to its link epoch."""

    connected: bool = True
    moving: bool = True
    excluded: bool = False
    recovered: bool = False
    epoch: int = 1
    commands: dict[str, CommandResult | None] = field(default_factory=dict)

    def issue_stop(self, command: str, *, passenger_status_known: bool) -> bool:
        """Exclude a selected problem vehicle and request a stop once."""
        if not self.connected or not passenger_status_known or command in self.commands:
            return False
        self.excluded = True
        self.recovered = False
        self.commands[command] = None
        return True

    def record_result(self, command: str, epoch: int, result: CommandResult) -> bool:
        """Record the response without treating acknowledgment as observed motion."""
        if not self.connected or epoch != self.epoch or command not in self.commands:
            return False
        previous = self.commands[command]
        if previous is not None and previous is not CommandResult.RECEIVED:
            return False
        self.commands[command] = result
        return True

    def observe_stop(self, command: str, epoch: int) -> bool:
        """Stop the motion view on a current physical event, not the response alone."""
        if not self.connected or epoch != self.epoch or command not in self.commands:
            return False
        if self.commands[command] in (CommandResult.REJECTED, CommandResult.FAILED):
            return False
        self.moving = False
        return True

    def local_stop(self) -> None:
        """Model vehicle-local stopping for an injected hazard or link loss."""
        self.moving = False

    def disconnect(self) -> None:
        """Invalidate the active link and immediately model a local stop."""
        self.connected = False
        self.local_stop()

    def reconnect(self) -> None:
        """Start a new command epoch without replaying prior requests."""
        if not self.connected:
            self.epoch += 1
            self.commands.clear()
            self.connected = True

    def recover(self, epoch: int, *, depot_arrival: bool) -> bool:
        """Recognize simulated recovery after the selected car is observed stopped."""
        if not (self.connected and self.excluded and depot_arrival):
            return False
        if epoch != self.epoch or self.moving:
            return False
        self.recovered = True
        return True

    def restore_dispatch(self, *, eligible: bool) -> bool:
        """Restore the recovered car only after separate eligibility checks pass."""
        if not (self.connected and self.recovered and eligible):
            return False
        self.excluded = False
        self.recovered = False
        return True
