"""In-memory mock payment and Dev-format garage events for SD-05 and SD-07."""

from dataclasses import dataclass, field
from enum import Enum


class PaymentResult(Enum):
    """Mock fare payment outcomes."""

    WAITING = 'waiting'
    PAID = 'paid'
    FAILED = 'failed'


@dataclass(frozen=True)
class Payment:
    """Synthetic fare in credits and the corresponding mock payment result."""

    fare_credits: int | None
    result: PaymentResult


@dataclass
class Billing:
    """Tiny fare ledger using only supplied synthetic inputs."""

    payments: dict[tuple[str, str], Payment] = field(default_factory=dict)

    def settle(
        self,
        trip_id: str,
        key: str,
        *,
        distance_m: int | None,
        duration_ticks: int | None,
        method_registered: bool,
        payment_succeeds: bool,
    ) -> Payment:
        """Compute an illustrative fare, then try mock payment idempotently."""
        previous = self.payments.get((trip_id, key))
        if previous is not None:
            return previous
        if distance_m is None or duration_ticks is None:
            return Payment(None, PaymentResult.WAITING)
        if distance_m < 0 or duration_ticks < 0:
            raise ValueError('negative mock fare input')
        fare = distance_m + duration_ticks
        if not method_registered:
            return Payment(fare, PaymentResult.WAITING)
        result = PaymentResult.PAID if payment_succeeds else PaymentResult.FAILED
        payment = Payment(fare, result)
        self.payments[trip_id, key] = payment
        return payment


class Purpose(Enum):
    """Mock SD-05/07 branch selected by the garage assignment."""

    PARK = 'park'
    CHARGE = 'charge'


class DepotState(Enum):
    """Separate vehicle arrival, equipment observation and release states."""

    RESERVED = 'reserved'
    ARRIVED = 'arrived'
    OCCUPIED = 'occupied'
    CHARGING = 'charging'
    WAITING = 'waiting'


@dataclass
class Slot:
    """Single synthetic bay; dispatch eligibility is evaluated after charging."""

    bay: str
    vehicle: str
    purpose: Purpose
    state: DepotState = DepotState.RESERVED
    exited: bool = False

    def observe(self, bay: str, vehicle: str, event: str) -> bool:
        """Advance only on a matching bay and vehicle event."""
        if (bay, vehicle) != (self.bay, self.vehicle):
            return False
        if event == 'exited' and self.state in (
            DepotState.OCCUPIED,
            DepotState.WAITING,
        ):
            if self.exited:
                return False
            self.exited = True
            return True
        transitions = {
            (DepotState.RESERVED, 'arrival'): DepotState.ARRIVED,
            (DepotState.ARRIVED, 'occupied'): DepotState.OCCUPIED,
        }
        if self.purpose is Purpose.CHARGE:
            transitions[DepotState.OCCUPIED, 'charge_started'] = DepotState.CHARGING
        next_state = transitions.get((self.state, event))
        if next_state is None or self.exited:
            return False
        self.state = next_state
        return True

    def apply_charge(self, bay: str, vehicle: str, battery_pct: int) -> bool:
        """Apply the state diagram's 70 percent boundary on a matching observation."""
        if (bay, vehicle) != (self.bay, self.vehicle):
            return False
        if self.state is not DepotState.CHARGING or not 70 <= battery_pct <= 100:
            return False
        self.state = DepotState.WAITING
        return True

    def eligible(self, *, connected: bool, battery_pct: int, required_pct: int) -> bool:
        """Reevaluate the next trip independently of the charging state transition."""
        return (
            self.exited
            and self.state in (DepotState.OCCUPIED, DepotState.WAITING)
            and connected
            and 0 <= required_pct <= battery_pct <= 100
        )
