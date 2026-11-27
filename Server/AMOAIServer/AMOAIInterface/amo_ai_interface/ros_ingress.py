"""Subscribe to Pinky front-camera topics and validate the IF-07 test input."""

import argparse
import logging
from collections.abc import Callable
from functools import partial

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import CompressedImage

from amo_ai_interface.deliver_frames import FrameDelivery
from amo_ai_interface.detector_config import add_detector_arguments, configure_targets
from amo_ai_interface.frame import (
    MAX_JPEG_BYTES,
    NS_PER_SECOND,
    Frame,
    is_jpeg,
    validate_robot_id,
)
from amo_ai_interface.vision_http import SERVICES, VisionTarget


def frame_from_message(robot_id: str, message: CompressedImage) -> Frame:
    """Convert a front optical JPEG on a configured robot's ROS topic.

    Require a matching header frame ID, explicit JPEG format, at most 2 MiB and
    a positive Unix timestamp with a valid ns component. Raise ValueError on
    malformed input without forwarding bytes.
    """
    stamp = message.header.stamp
    if (
        message.header.frame_id != f'{robot_id}/front_optical_frame'
        or message.format != 'jpeg'
        or stamp.sec < 0
        or not 0 <= stamp.nanosec < NS_PER_SECOND
        or not (stamp.sec or stamp.nanosec)
        or not 5 <= len(message.data) <= MAX_JPEG_BYTES
    ):
        raise ValueError('Invalid camera header, JPEG format, stamp, or size')

    image = bytes(message.data)
    if not is_jpeg(image):
        raise ValueError('Invalid camera JPEG envelope')
    return Frame(robot_id, stamp.sec * NS_PER_SECOND + stamp.nanosec, image)


def _receive(
    message: CompressedImage, *, robot_id: str, offer: Callable[[Frame], None]
) -> None:
    try:
        frame = frame_from_message(robot_id, message)
    except ValueError:
        logging.warning('camera_frame_rejected robot=%s', robot_id)
        return
    logging.info(
        'camera_frame_received robot=%s frame=%s stamp_ns=%d bytes=%d',
        frame.robot_id,
        frame.frame_id,
        frame.stamp_ns,
        len(frame.jpeg),
    )
    offer(frame)


def _spin(robot_ids: frozenset[str], delivery: FrameDelivery) -> None:
    qos = QoSProfile(
        depth=1,
        reliability=ReliabilityPolicy.BEST_EFFORT,
        durability=DurabilityPolicy.VOLATILE,
    )
    rclpy.init(args=[])
    try:
        node = rclpy.create_node('amo_ai_interface')
        try:
            for robot_id in sorted(robot_ids):
                topic = f'/amo/{robot_id}/camera/compressed'
                node.create_subscription(
                    CompressedImage,
                    topic,
                    partial(_receive, robot_id=robot_id, offer=delivery.offer),
                    qos,
                )
                logging.info('camera_ingress_ready robot=%s topic=%s', robot_id, topic)
            rclpy.spin(node)
        finally:
            node.destroy_node()
    finally:
        rclpy.try_shutdown()


def main() -> int:
    """Run diagnostics or one enabled detector on ROS 2 Jazzy.

    Configure at most 16 distinct robot IDs and the applicable /infer URLs.
    The process owns the ROS node and HTTP worker for its lifetime.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--robot-id', action='append', required=True)
    parser.add_argument('--driving-perception-url')
    parser.add_argument('--traffic-rules-url')
    parser.add_argument('--direction-recognition-url')
    add_detector_arguments(parser)
    arguments = parser.parse_args()
    try:
        robot_ids = frozenset(map(validate_robot_id, arguments.robot_id))
        if len(robot_ids) != len(arguments.robot_id) or len(robot_ids) > 16:
            raise ValueError('Supply 1–16 distinct robot IDs')
        targets = tuple(
            VisionTarget(vision_id, url)
            for vision_id, service in SERVICES.items()
            if (url := getattr(arguments, f'{service.replace("-", "_")}_url'))
        )
        if arguments.detector_service is None and len(targets) != len(SERVICES):
            raise ValueError('Supply all three Vision URLs in receipt diagnostics mode')
        operations = configure_targets(arguments, targets, robot_ids)
    except ValueError as error:
        parser.error(str(error))

    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    try:
        with FrameDelivery(
            robot_ids, operations, arguments.detector_service
        ) as delivery:
            _spin(robot_ids, delivery)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
