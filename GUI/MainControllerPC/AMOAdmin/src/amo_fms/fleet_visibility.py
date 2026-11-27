"""Project IF-03 observations into the FMS presentation mode."""

from dataclasses import replace

from .models import Event, Snapshot, Vehicle


def is_scenario_vehicle(number: str) -> bool:
    """Match the reserved replay fixture and numbered scenario fixtures."""
    return number == 'DEMO-REPLAY-01' or (
        number.startswith('DEMO-REVIEW-')
        and number.removeprefix('DEMO-REVIEW-').isdecimal()
    )


def visible_fleet(snapshot: Snapshot, scenario_demo: bool) -> Snapshot:
    """Return the view snapshot without changing the received IF-03 observations."""
    if scenario_demo:
        return snapshot
    vehicles = tuple(v for v in snapshot.vehicles if not is_scenario_vehicle(v.number))
    simulated = {v.number for v in vehicles if _is_demo_reading(v)}
    return replace(
        snapshot,
        vehicles=tuple(
            _without_demo_observations(v) if v.number in simulated else v
            for v in vehicles
        ),
        pinky_batteries=tuple(
            row for row in snapshot.pinky_batteries if not row.simulated
        ),
        review=None,
        events=tuple(
            event
            for event in snapshot.events
            if not event.type.startswith('DEMO_REVIEW_')
            and not is_scenario_vehicle(event.vehicle)
            and not (event.vehicle in simulated and event.type == 'CHARGING')
        ),
    )


def _is_demo_reading(vehicle: Vehicle) -> bool:
    return vehicle.connection.upper() == 'SIMULATED' or (
        vehicle.sample is not None
        and vehicle.sample[0].startswith(('demo-', 'review-'))
    )


def _without_demo_observations(vehicle: Vehicle) -> Vehicle:
    return replace(
        vehicle,
        status='UNKNOWN',
        battery_percent=None,
        connection='UNKNOWN',
        stop_reason='',
        position_m=None,
        yaw_rad=None,
        speed_mps=None,
        sample=None,
    )


def latest_review_stage(snapshot: Snapshot) -> Event | None:
    """Read the latest committed review stage carried by legacy IF-03 snapshots."""
    return next((e for e in snapshot.events if e.type.startswith('DEMO_REVIEW_')), None)


def scenario_vehicle(snapshot: Snapshot) -> Vehicle | None:
    """Return the display identity of the current review or the legacy fixture."""
    fixtures = tuple(v for v in snapshot.vehicles if is_scenario_vehicle(v.number))
    review = snapshot.review
    if review is None:
        stage = latest_review_stage(snapshot)
        number = stage.vehicle if stage else 'DEMO-REPLAY-01'
        return next((v for v in fixtures if v.number == number), None)
    matching = next((v for v in fixtures if v.number == review.vehicle), None)
    checkpoint = review.checkpoints[-1] if review.checkpoints else None
    if matching is not None:
        return replace(matching, status=checkpoint.status) if checkpoint else matching
    return Vehicle(
        id=f'scenario:{review.run_id}',
        number=review.vehicle,
        status=checkpoint.status if checkpoint else 'UNKNOWN',
        battery_percent=None,
        connection='SIMULATED',
        stop_reason=checkpoint.reason if checkpoint else '',
        position_m=None,
        yaw_rad=None,
        speed_mps=None,
        dispatch_enabled=None,
    )
