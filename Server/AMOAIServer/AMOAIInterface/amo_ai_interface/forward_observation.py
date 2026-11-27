"""Orchestrate detection and publication through explicit application ports."""

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from uuid import uuid4

from amo_ai_interface.frame import Frame
from amo_ai_interface.observation import observation_payload, parse_detection

Detector = Callable[[Frame], object]
ObservationWriter = Callable[[dict[str, str | float]], None]


@dataclass(frozen=True, slots=True)
class ForwardObservation:
    """Publish one real detector result for a mapped camera and selected source."""

    source: str
    vehicles: Mapping[str, str]
    detect: Detector
    write: ObservationWriter

    def __call__(self, frame: Frame) -> None:
        """Resolve the vehicle, validate the response and submit its metadata.

        Raise ValueError for an unmapped camera or an invalid detector result.
        Failed requests propagate to the frame dispatcher's error handler.
        """
        vehicle_no = self.vehicles.get(frame.robot_id)
        if vehicle_no is None:
            raise ValueError('Camera has no AMO vehicle mapping')
        detection = parse_detection(self.detect(frame), frame)
        result_id = uuid4()
        self.write(
            observation_payload(frame, detection, vehicle_no, self.source, result_id)
        )
        logging.info(
            'vision_observation_acknowledged robot=%s frame=%s source=%s result=%s',
            frame.robot_id,
            frame.frame_id,
            self.source,
            result_id,
        )
