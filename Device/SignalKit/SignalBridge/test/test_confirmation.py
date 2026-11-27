"""Unit tests for command confirmation and resend limits."""

import pytest

from amode_signal_bridge.confirmation import Action, CommandConfirmation
from amode_signal_bridge.state_document import parse_state


def test_waits_until_the_timeout_then_resends_the_whole_batch() -> None:
    tracker = CommandConfirmation(timeout_s=2.0, max_attempts=3)
    tracker.sent('HOLD NORTH_GREEN', 10.0)
    tracker.sent('PLAN 15000 8000 3000 2000', 10.5)
    assert tracker.poll(12.4).action is Action.WAIT
    decision = tracker.poll(12.5)
    assert decision.action is Action.RESEND
    assert decision.commands == ('HOLD NORTH_GREEN', 'PLAN 15000 8000 3000 2000')


def test_the_newest_command_confirms_the_batch() -> None:
    tracker = CommandConfirmation()
    tracker.sent('AUTO', 0.0)
    tracker.sent('PLAN 10000 10000 3000 2000', 0.0)
    tracker.observe('AUTO')
    assert tracker.pending == ('AUTO', 'PLAN 10000 10000 3000 2000')
    tracker.observe('PLAN 10000 10000 3000 2000')
    assert tracker.pending == ()
    assert tracker.poll(100.0).action is Action.WAIT


def test_gives_up_after_the_last_attempt() -> None:
    tracker = CommandConfirmation(timeout_s=1.0, max_attempts=3)
    tracker.sent('HOLD ALL_RED', 0.0)
    assert tracker.poll(1.0).action is Action.RESEND
    assert tracker.poll(2.0).action is Action.RESEND
    decision = tracker.poll(3.0)
    assert decision.action is Action.GIVE_UP
    assert decision.commands == ('HOLD ALL_RED',)
    assert tracker.pending == ()


def test_a_new_command_restarts_the_attempt_count() -> None:
    tracker = CommandConfirmation(timeout_s=1.0, max_attempts=2)
    tracker.sent('AUTO', 0.0)
    assert tracker.poll(1.0).action is Action.RESEND
    tracker.sent('HOLD EAST_GREEN', 1.5)
    assert tracker.poll(2.5).action is Action.RESEND


def test_rejects_invalid_limits() -> None:
    with pytest.raises(ValueError):
        CommandConfirmation(timeout_s=0)
    with pytest.raises(ValueError):
        CommandConfirmation(max_attempts=0)


def test_parse_state_accepts_only_json_objects() -> None:
    assert parse_state('{"signalId": "SIG-01"}') == {'signalId': 'SIG-01'}
    assert parse_state('[1, 2]') is None
    assert parse_state('not json') is None
