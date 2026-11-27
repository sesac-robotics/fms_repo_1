"""In-memory call deduplication, queue waiting and dispatch for SD-01 and SD-02."""

from collections.abc import Iterable
from dataclasses import dataclass, field

from one_way_trip import Call, Candidate, Receipt, Trip


@dataclass
class Intake:
    """Minimal member, call and dispatch fixture. No writes to external storage."""

    members: set[str] = field(default_factory=set)
    receipts: dict[tuple[str, str], Receipt] = field(default_factory=dict)
    trips: dict[str, Trip] = field(default_factory=dict)
    waiting: dict[str, str] = field(default_factory=dict)

    def register(self, member: str) -> None:
        """Add a synthetic member ID for the mock scenario."""
        self.members.add(member)

    def accept(self, call: Call, *, accepted_at: int) -> Receipt:
        """Deduplicate the same request and reject unknown members or key reuse."""
        if call.member not in self.members:
            raise ValueError('unknown member')
        if not call.key or not call.origin or not call.destination:
            raise ValueError('incomplete request')
        key = call.member, call.key
        previous = self.receipts.get(key)
        if previous is not None:
            if previous.call != call:
                raise ValueError('request key collision')
            return previous
        if accepted_at < call.requested_at:
            raise ValueError('intake precedes request')
        receipt = Receipt(f'T{len(self.receipts) + 1}', call, accepted_at)
        self.receipts[key] = receipt
        return receipt

    def dispatch(
        self, receipt: Receipt, candidates: Iterable[Candidate], *, epoch: int
    ) -> Trip | None:
        """Choose the first synthetic ETA, then vehicle ID, after eligibility checks."""
        if self.receipts.get((receipt.call.member, receipt.call.key)) != receipt:
            raise ValueError('unknown receipt')
        if receipt.trip_id in self.trips:
            return self.trips[receipt.trip_id]
        occupied = {trip.candidate.vehicle for trip in self.trips.values()}
        eligible = (
            c
            for c in candidates
            if c.vehicle not in occupied
            and c.available
            and c.connected
            and c.battery_pct >= c.required_pct
            and c.route_open
        )
        choice = min(eligible, key=lambda c: (c.eta, c.vehicle), default=None)
        if choice is None:
            self.waiting[receipt.trip_id] = 'no_eligible_vehicle'
            return None
        self.waiting.pop(receipt.trip_id, None)
        trip = Trip(receipt, choice, epoch, f'A{len(self.trips) + 1}')
        self.trips[receipt.trip_id] = trip
        return trip
