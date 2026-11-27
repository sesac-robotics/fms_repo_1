"""ROS 2 node relaying one SignalKit traffic light to AMO Main Control.

Subscribes:  /<signal_namespace>/state  std_msgs/String  JSON, best effort
Publishes:   /<signal_namespace>/cmd    std_msgs/String  command text, reliable
Parameters:  signal_namespace (str, e.g. traffic_light_1)
             period_s (float seconds in [0.1, 5.0], default 0.5)
Environment: AMO_SIGNAL_INGEST_KEY (required), AMO_CONTROL_URL

Every period the node forwards the newest state, claims queued staff commands
and publishes them, and resends commands the signal has not confirmed. HTTP
runs on one worker thread so ROS callbacks never wait on the network; a
period is skipped while the previous exchange is still running.
"""

from __future__ import annotations

import os
import re
import sys
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from std_msgs.msg import String

from .confirmation import Action, CommandConfirmation
from .control_client import ControlClient, ControlUnavailable
from .state_document import parse_state

NAMESPACE = re.compile(r'[a-z][a-z0-9_]{0,63}')


class SignalBridge(Node):
    """Relays one signal's state up and staff commands down."""

    def __init__(self, client: ControlClient) -> None:
        """Validate parameters and create the topics, timer and worker."""
        super().__init__('amo_signal_bridge')
        namespace = self.declare_parameter('signal_namespace', 'traffic_light_1').value
        period = self.declare_parameter('period_s', 0.5).value
        if not isinstance(namespace, str) or not NAMESPACE.fullmatch(namespace):
            raise ValueError('signal_namespace must match [a-z][a-z0-9_]{0,63}')
        if not isinstance(period, float) or not 0.1 <= period <= 5.0:
            raise ValueError('period_s must be a float in [0.1, 5.0]')
        self._client = client
        self._lock = threading.Lock()
        self._latest: dict[str, object] | None = None
        self._fresh = False
        # 5 attempts x 2 s covers an agent restart plus the ~2 s the ESP32 needs to
        # rejoin; a longer outage is logged so staff can resend.
        self._confirmation = CommandConfirmation(timeout_s=2.0, max_attempts=5)
        self._failing = False
        self._worker = ThreadPoolExecutor(max_workers=1)
        self._running: Future[None] | None = None
        state_qos = QoSProfile(depth=5, reliability=ReliabilityPolicy.BEST_EFFORT)
        command_qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        self.create_subscription(
            String, f'/{namespace}/state', self._on_state, state_qos
        )
        self._commands = self.create_publisher(String, f'/{namespace}/cmd', command_qos)
        self.create_timer(period, self._on_timer)
        self.get_logger().info(f'bridging /{namespace} every {period:.1f} s')

    def destroy_node(self) -> None:
        """Let the current HTTP exchange finish (bounded by its timeout) first."""
        self._worker.shutdown(wait=True)
        super().destroy_node()

    def _on_state(self, message: String) -> None:
        document = parse_state(message.data)
        if document is None:
            self.get_logger().warning('ignored a state message that is not valid JSON')
            return
        with self._lock:
            self._latest = document
            self._fresh = True
            self._confirmation.observe(document.get('lastCommand'))

    def _on_timer(self) -> None:
        if self._running is None or self._running.done():
            self._running = self._worker.submit(self._exchange)

    def _exchange(self) -> None:
        with self._lock:
            document = self._latest if self._fresh else None
            self._fresh = False
            signal_id = self._latest.get('signalId') if self._latest else None
        try:
            if document is not None:
                status = self._client.post_state(document)
                if status != 204:
                    self.get_logger().warning(f'state rejected with HTTP {status}')
            if isinstance(signal_id, str):
                for item in self._client.claim_commands(signal_id):
                    self._publish(item.command, track=True)
                    self.get_logger().info(f'command #{item.id}: {item.command}')
            self._report(ok=True)
        except ControlUnavailable as failure:
            self._report(ok=False, reason=str(failure))
        self._retry_unconfirmed()

    def _publish(self, command: str, track: bool) -> None:
        self._commands.publish(String(data=command))
        if track:
            with self._lock:
                self._confirmation.sent(command, time.monotonic())

    def _retry_unconfirmed(self) -> None:
        with self._lock:
            decision = self._confirmation.poll(time.monotonic())
        if decision.action is Action.RESEND:
            self.get_logger().warning(f'resending {list(decision.commands)}')
            for command in decision.commands:
                self._publish(command, track=False)
        elif decision.action is Action.GIVE_UP:
            self.get_logger().error(f'signal did not confirm {list(decision.commands)}')

    def _report(self, ok: bool, reason: str = '') -> None:
        # Log transitions only, so an unreachable server does not flood the console.
        if ok and self._failing:
            self.get_logger().info('Main Control reachable again')
        elif not ok and not self._failing:
            self.get_logger().error(f'Main Control unreachable: {reason}')
        self._failing = not ok


def main() -> int:
    """Run the bridge until interrupted; exit code 2 for missing configuration."""
    url = os.environ.get('AMO_CONTROL_URL', 'http://127.0.0.1:18088')
    try:
        client = ControlClient(url, os.environ.get('AMO_SIGNAL_INGEST_KEY', ''))
    except ValueError as error:
        print(f'{error} (set AMO_SIGNAL_INGEST_KEY like Main Control)', file=sys.stderr)
        return 2
    rclpy.init()
    node = SignalBridge(client)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
