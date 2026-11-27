"""Run the installed ROS camera and AI Interface with a synthetic MJPEG source."""

import os
import re
import signal
import subprocess
import sys
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory

from test_vision_receipts import JPEG, running_receipt

_ROBOT = 'pinky_transport_test'
_FRAME_COUNT = 6


def _write_camera(directory: Path) -> None:
    executable = directory / 'rpicam-vid'
    executable.write_text(
        f'#!{sys.executable}\n'
        'import sys\n'
        'from time import sleep\n'
        'expected = {\n'
        "    '--width': '640', '--height': '480', '--framerate': '5',\n"
        "    '--rotation': '180', '--codec': 'mjpeg', '--output': '-',\n"
        '}\n'
        'for name, value in expected.items():\n'
        '    assert sys.argv[sys.argv.index(name) + 1] == value\n'
        f'for _ in range({_FRAME_COUNT}):\n'
        f'    sys.stdout.buffer.write({JPEG!r})\n'
        '    sys.stdout.buffer.flush()\n'
        '    sleep(0.25)\n',
        encoding='utf-8',
    )
    executable.chmod(0o700)


def _stop_ingress(process: subprocess.Popen[str]) -> str:
    process.send_signal(signal.SIGINT)
    try:
        return process.communicate(timeout=8)[0]
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate(timeout=3)
        raise


def main() -> int:
    """Use an isolated local DDS domain and ephemeral loopback HTTP bindings."""
    if os.environ.get('ROS_DISTRO') != 'jazzy':
        raise RuntimeError('Source ROS 2 Jazzy and the two AMO packages first')
    with ExitStack() as stack:
        urls = [
            stack.enter_context(running_receipt(vision_id)) for vision_id in (1, 2, 3)
        ]
        directory = Path(stack.enter_context(TemporaryDirectory(prefix='amo-vision-')))
        _write_camera(directory)
        env = {
            **os.environ,
            'PATH': f'{directory}:{os.environ["PATH"]}',
            'ROS_DOMAIN_ID': os.environ.get('AMO_TEST_ROS_DOMAIN_ID', '172'),
            'ROS_AUTOMATIC_DISCOVERY_RANGE': 'LOCALHOST',
            'ROS_STATIC_PEERS': '',
            'ROS_LOG_DIR': str(directory / 'ros-log'),
        }
        ingress = subprocess.Popen(
            [
                sys.executable,
                '-m',
                'amo_ai_interface.ros_ingress',
                '--robot-id',
                _ROBOT,
                '--driving-perception-url',
                urls[0],
                '--traffic-rules-url',
                urls[1],
                '--direction-recognition-url',
                urls[2],
            ],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            publisher = subprocess.run(
                [
                    sys.executable,
                    '-m',
                    'amo_camera_streamer.ros_publisher',
                    '--robot-id',
                    _ROBOT,
                    '--frames',
                    str(_FRAME_COUNT),
                ],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=35,
                check=False,
            )
        finally:
            ingress_log = _stop_ingress(ingress)
            print(ingress_log, end='')
        print(publisher.stdout, end='')
        if publisher.returncode or ingress.returncode:
            raise RuntimeError(
                'The camera publisher or AI Interface exited with an error'
            )

        sent = set(re.findall(r'camera_frame_sent .* stamp_ns=(\d+)', publisher.stdout))
        arrivals = dict(
            re.findall(
                r'camera_frame_received .* frame=([0-9a-f]{32}) stamp_ns=(\d+)',
                ingress_log,
            )
        )
        confirmed = set(
            re.findall(
                r'vision_receipts .* frame=([0-9a-f]{32}) confirmed=3/3', ingress_log
            )
        )
        if (
            len(sent) != _FRAME_COUNT
            or not confirmed
            or not confirmed <= arrivals.keys()
        ):
            raise RuntimeError(
                'No correlated full HTTP receipt for the published test frames'
            )
        if not set(arrivals.values()) <= sent:
            raise RuntimeError(
                'ROS ingress logged a frame that the test camera did not publish'
            )
        print(
            f'Synthetic MJPEG sent={len(sent)} ROS received={len(arrivals)} all three HTTP receipts={len(confirmed)}'
        )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
