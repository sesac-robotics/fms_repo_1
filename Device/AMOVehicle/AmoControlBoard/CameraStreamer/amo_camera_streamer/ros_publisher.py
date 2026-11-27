"""Publish front optical JPEGs on a per-Pinky ROS 2 Jazzy topic."""

import argparse
import logging
import re
import signal
from itertools import islice
from time import monotonic, monotonic_ns, time_ns
from types import FrameType

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from rclpy.signals import SignalHandlerOptions
from sensor_msgs.msg import CompressedImage

from amo_camera_streamer.camera_capture import jpeg_frames, open_camera

_NS_PER_SECOND = 1_000_000_000


def camera_message(robot_id: str, jpeg: bytes, stamp_ns: int) -> CompressedImage:
    """Build a JPEG message stamped in Unix ns at frame acquisition from stdout.

    The frame ID is the Pinky's front optical frame. The caller supplies a
    validated robot ID, complete JPEG and positive ROS-representable stamp.
    """
    message = CompressedImage()
    message.header.frame_id = f'{robot_id}/front_optical_frame'
    stamp = message.header.stamp
    stamp.sec, stamp.nanosec = divmod(stamp_ns, _NS_PER_SECOND)
    message.format = 'jpeg'
    message.data = jpeg
    return message


def _publish(node: Node, robot_id: str, count: int | None) -> None:
    topic = f'/amo/{robot_id}/camera/compressed'
    qos = QoSProfile(
        depth=1,
        reliability=ReliabilityPolicy.BEST_EFFORT,
        durability=DurabilityPolicy.VOLATILE,
    )
    publisher = node.create_publisher(CompressedImage, topic, qos)
    deadline = monotonic() + 25
    while rclpy.ok() and publisher.get_subscription_count() == 0:
        if monotonic() >= deadline:
            raise RuntimeError(f'No camera subscriber discovered for {topic}')
        rclpy.spin_once(node, timeout_sec=0.1)
    if not rclpy.ok():
        return

    logging.info('camera_publisher_ready robot=%s topic=%s', robot_id, topic)
    epoch_offset = time_ns() - monotonic_ns()
    sent = 0
    with open_camera() as stream:
        for jpeg in islice(jpeg_frames(stream), count):
            if not rclpy.ok():
                return
            stamp_ns = epoch_offset + monotonic_ns()
            publisher.publish(camera_message(robot_id, jpeg, stamp_ns))
            sent += 1
            logging.info(
                'camera_frame_sent robot=%s stamp_ns=%d bytes=%d',
                robot_id,
                stamp_ns,
                len(jpeg),
            )
        if sent != count and rclpy.ok():
            raise RuntimeError(f'Camera stopped after {sent} frames')


def _stop_camera(_signum: int, _frame: FrameType | None) -> None:
    raise KeyboardInterrupt


def main() -> int:
    """Run the camera-only node with explicit identity and optional frame limit.

    The caller owns DDS environment configuration. The node releases its
    publisher and camera on exit. Return 1 on startup or capture failure.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--robot-id', required=True)
    parser.add_argument('--frames', type=int)
    arguments = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,31}', arguments.robot_id):
        parser.error('--robot-id must contain 1–32 characters valid in a ROS subtopic')
    if arguments.frames is not None and arguments.frames < 1:
        parser.error('--frames must be positive')

    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    previous_term = signal.signal(signal.SIGTERM, _stop_camera)
    try:
        rclpy.init(args=[], signal_handler_options=SignalHandlerOptions.NO)
        try:
            node = rclpy.create_node(f'amo_camera_{arguments.robot_id}')
            try:
                _publish(node, arguments.robot_id, arguments.frames)
            finally:
                node.destroy_node()
        finally:
            rclpy.try_shutdown()
    except KeyboardInterrupt:
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        logging.error('camera_publisher_failed: %s', error)
        return 1
    finally:
        signal.signal(signal.SIGTERM, previous_term)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
