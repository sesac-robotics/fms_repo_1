"""Synthetic SD-08 and SD-09 vehicle evidence shared by the offline fixtures."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Scope:
    """Trip, assigned vehicle and monotonic fixture connection generation."""

    trip: str
    assignment: str
    vehicle: str
    epoch: int


@dataclass(frozen=True)
class Evidence:
    """Sequenced controller report in one fixture epoch, scoped to one command."""

    scope: Scope
    command: str
    sequence: int
