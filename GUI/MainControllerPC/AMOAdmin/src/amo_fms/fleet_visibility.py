"""Project IF-03 observations into the FMS presentation mode."""

from dataclasses import replace

from .models import Snapshot


def _is_scenario_vehicle(number: str) -> bool:
    # Match the reserved replay fixture and numbered scenario fixtures.
    return number == 'DEMO-REPLAY-01' or (
        number.startswith('DEMO-REVIEW-')
        and number.removeprefix('DEMO-REVIEW-').isdecimal()
    )


def visible_fleet(snapshot: Snapshot, scenario_demo: bool) -> Snapshot:
    """Return the view snapshot without changing the received IF-03 observations."""
    if scenario_demo:
        return snapshot
    return replace(
        snapshot,
        vehicles=tuple(
            v for v in snapshot.vehicles if not _is_scenario_vehicle(v.number)
        ),
        review=None,
        events=tuple(
            event
            for event in snapshot.events
            if not event.type.startswith('DEMO_REVIEW_')
            and not _is_scenario_vehicle(event.vehicle)
        ),
    )
