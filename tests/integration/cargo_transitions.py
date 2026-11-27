"""Define SD-11 stages and admissible sources for the synthetic Cargo fixture."""

from enum import Enum


class State(Enum):
    """Test stages from pickup facility through verified return."""

    TO_CARGO_DEPOT = 'cargo_depot_travel'
    STOPPED_FOR_LOAD = 'cargo_depot_stopped'
    COUPLING_WAIT = 'coupling_wait'
    COUPLED = 'coupled'
    TO_PICKUP = 'pickup_travel'
    BOARDING_WAIT = 'boarding_wait'
    BOARDED = 'boarded'
    TRANSPORT = 'loaded_travel'
    STOPPED_FOR_HANDOFF = 'handoff_stopped'
    RETURN_TO_CARGO_DEPOT = 'cargo_depot_return'
    RELEASE_WAIT = 'uncoupling_wait'
    RELEASE_BLOCKED = 'uncoupling_blocked'
    RESTORE_WAIT = 'normal_config_wait'
    RETURN_TO_GARAGE = 'garage_return'
    RETURNED = 'garage_arrived'


class Event(Enum):
    """Explicit evidence kinds so hardware outcomes cannot stand in for motion."""

    LOAD_STOP = 'load_stop'
    LOADED = 'loaded'
    COUPLED = 'coupled'
    LOADED_MODE = 'loaded_mode_applied'
    PICKUP_STOP = 'pickup_stop'
    BOARDING_CONFIRMED = 'boarding_confirmed'
    DEPARTED = 'departed'
    HANDOFF_STOP = 'handoff_stop'
    HANDOFF = 'cargo_handoff'
    RELEASE_STOP = 'release_stop'
    DETACHED = 'detached'
    RELEASE_FAILED = 'release_failed'
    NORMAL_MODE = 'normal_mode_restored'
    GARAGE_ARRIVAL = 'garage_arrival'


# Acknowledgements are intentionally outside this table of applied/observed events.
TRANSITIONS = {
    (State.TO_CARGO_DEPOT, Event.LOAD_STOP): (
        State.STOPPED_FOR_LOAD,
        'origin',
        'IF-05',
    ),
    (State.STOPPED_FOR_LOAD, Event.LOADED): (State.COUPLING_WAIT, 'origin', 'IF-13'),
    (State.COUPLING_WAIT, Event.COUPLED): (State.COUPLED, 'origin', 'IF-13'),
    (State.COUPLED, Event.LOADED_MODE): (State.TO_PICKUP, 'origin', 'IF-05'),
    (State.TO_PICKUP, Event.PICKUP_STOP): (State.BOARDING_WAIT, 'pickup', 'IF-05'),
    (State.BOARDING_WAIT, Event.BOARDING_CONFIRMED): (
        State.BOARDED,
        'pickup',
        'mock_c03',
    ),
    (State.BOARDED, Event.DEPARTED): (State.TRANSPORT, 'pickup', 'IF-05'),
    (State.TRANSPORT, Event.HANDOFF_STOP): (
        State.STOPPED_FOR_HANDOFF,
        'destination',
        'IF-05',
    ),
    (State.STOPPED_FOR_HANDOFF, Event.HANDOFF): (
        State.RETURN_TO_CARGO_DEPOT,
        'destination',
        'mock_handoff',
    ),
    (State.RETURN_TO_CARGO_DEPOT, Event.RELEASE_STOP): (
        State.RELEASE_WAIT,
        'release_site',
        'IF-05',
    ),
    (State.RELEASE_WAIT, Event.DETACHED): (State.RESTORE_WAIT, 'release_site', 'IF-13'),
    (State.RELEASE_WAIT, Event.RELEASE_FAILED): (
        State.RELEASE_BLOCKED,
        'release_site',
        'IF-13',
    ),
    (State.RESTORE_WAIT, Event.NORMAL_MODE): (
        State.RETURN_TO_GARAGE,
        'release_site',
        'IF-05',
    ),
    (State.RETURN_TO_GARAGE, Event.GARAGE_ARRIVAL): (State.RETURNED, 'garage', 'IF-05'),
}
