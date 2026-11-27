"""Build the optional Vision observation route from operator-supplied settings."""

import argparse
import os
import re
from functools import partial
from pathlib import Path

from amo_ai_interface.deliver_frames import FrameOperation
from amo_ai_interface.forward_observation import ForwardObservation
from amo_ai_interface.frame import validate_robot_id
from amo_ai_interface.main_control_http import MainControlWriter
from amo_ai_interface.vision_http import (
    SERVICES,
    VisionTarget,
    confirm_receipt,
    request_inference,
)

_VEHICLE_ID = re.compile(r'[A-Za-z0-9_-]{1,64}')


def add_detector_arguments(parser: argparse.ArgumentParser) -> None:
    """Register the explicit opt-in for one detector and its private settings."""
    parser.add_argument('--detector-service', choices=tuple(SERVICES.values()))
    parser.add_argument('--vehicle-map', action='append', metavar='ROBOT=VEHICLE')
    parser.add_argument('--main-control-url')


def configure_targets(
    arguments: argparse.Namespace,
    targets: tuple[VisionTarget, ...],
    robot_ids: frozenset[str],
) -> dict[str, FrameOperation]:
    """Select one detector when requested and preserve other diagnostic routes.

    The enabled detector requires a distinct vehicle for each robot, a local
    Main Control URL and a readable key path in AMO_VISION_KEY_FILE.
    """
    operations: dict[str, FrameOperation] = {
        target.service: partial(confirm_receipt, target) for target in targets
    }
    service = arguments.detector_service
    if service is None:
        if arguments.vehicle_map or arguments.main_control_url:
            raise ValueError(
                'Vehicle mapping and Main Control require --detector-service'
            )
        return operations
    vehicles = _vehicle_mapping(arguments.vehicle_map or [], robot_ids)
    if not arguments.main_control_url:
        raise ValueError('--main-control-url is required in detector mode')
    key = _read_key()
    writer = MainControlWriter(arguments.main_control_url, key)
    target = next((target for target in targets if target.service == service), None)
    if target is None:
        raise ValueError('Supply the selected detector service URL')
    operations[service] = ForwardObservation(
        service.upper().replace('-', '_'),
        vehicles,
        partial(request_inference, target),
        writer.send,
    )
    return operations


def _vehicle_mapping(entries: list[str], robot_ids: frozenset[str]) -> dict[str, str]:
    vehicles = {}
    for entry in entries:
        robot, _, vehicle = entry.partition('=')
        validate_robot_id(robot)
        if not _VEHICLE_ID.fullmatch(vehicle) or robot in vehicles:
            raise ValueError('Supply each --vehicle-map once as ROBOT=VEHICLE')
        vehicles[robot] = vehicle
    if vehicles.keys() != robot_ids or len(set(vehicles.values())) != len(vehicles):
        raise ValueError('Map each configured robot to a distinct AMO vehicle')
    return vehicles


def _read_key() -> str:
    filename = os.environ.get('AMO_VISION_KEY_FILE')
    if not filename:
        raise ValueError('Set AMO_VISION_KEY_FILE to a readable secret file')
    try:
        with Path(filename).open(encoding='ascii') as file:
            return file.read(4097).rstrip('\r\n')
    except (OSError, UnicodeError) as error:
        raise ValueError('Could not read the Vision key file') from error
