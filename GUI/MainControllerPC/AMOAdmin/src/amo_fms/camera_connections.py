"""Own optional camera-only SSH processes for explicitly configured fleet slots."""

import json
import os
import re
import shlex
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, QProcessEnvironment, pyqtSignal

from .camera_askpass import private_bytes


@dataclass(frozen=True, slots=True)
class CameraTarget:
    """Private SSH endpoint and deployed ROS camera environment."""

    destination: str
    robot_id: str
    setup: str

    @classmethod
    def parse(cls, value: object) -> 'CameraTarget':
        """Validate a server alias or IPv4/hostname and shell-independent inputs."""
        if not isinstance(value, dict):
            raise ValueError('Expected camera target.')
        destination, robot, setup = (
            value.get(key) for key in ('destination', 'robot_id', 'setup')
        )
        if (
            not isinstance(destination, str)
            or not re.fullmatch(r'[a-zA-Z0-9_][\w.-]*@[a-zA-Z0-9][\w.-]*', destination)
            or not isinstance(robot, str)
            or not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_]{0,31}', robot)
            or not isinstance(setup, str)
            or not setup.startswith('/')
            or any(char in setup for char in '\r\n\x00')
        ):
            raise ValueError('Invalid camera target.')
        return cls(destination, robot, setup)

    def ssh_arguments(self) -> list[str]:
        """Build the fixed capture-only command for a known SSH host."""
        script = shlex.join(['source', self.setup])
        camera = shlex.join(
            [
                'ros2',
                'run',
                'amo_camera_streamer',
                'camera_streamer',
                '--robot-id',
                self.robot_id,
            ]
        )
        return [
            '-F',
            '/dev/null',
            '-tt',
            '-o',
            'StrictHostKeyChecking=yes',
            '-o',
            'ClearAllForwardings=yes',
            '-o',
            'ConnectTimeout=8',
            '-o',
            'ServerAliveInterval=5',
            '-o',
            'ServerAliveCountMax=2',
            '-o',
            'NumberOfPasswordPrompts=1',
            '-o',
            'PreferredAuthentications=password',
            '-o',
            'PubkeyAuthentication=no',
            self.destination,
            shlex.join(['bash', '-c', f'{script} && exec {camera}']),
        ]


class CameraConnections(QObject):
    """Track one nonblocking SSH connection per registered camera slot."""

    changed = pyqtSignal(str)

    def __init__(self, parent: QObject) -> None:
        """Load explicit private configuration only when live connections are enabled."""
        super().__init__(parent)
        self._processes: dict[str, QProcess] = {}
        self._failed: set[str] = set()
        self._targets: dict[str, CameraTarget] = {}
        self._helper = Path(sys.executable).with_name('amo-camera-askpass')
        self._password = Path.home() / '.config/amo/pinky-camera-password'
        self._ssh = shutil.which('ssh')
        if os.environ.get('AMO_FMS_CAMERA_SSH') != '1' or not self._ssh:
            return
        try:
            config = Path.home() / '.config/amo/pinky-camera-targets.json'
            targets = json.loads(private_bytes(config, 8192))
            if not isinstance(targets, dict) or any(
                not re.fullmatch(r'PINKY-0[1-4]', slot) for slot in targets
            ):
                return
            self._targets = {
                slot: CameraTarget.parse(value) for slot, value in targets.items()
            }
        except (OSError, ValueError):
            pass

    def available(self, slot: str) -> bool:
        """Return whether an explicitly enabled slot has an installed SSH adapter."""
        return (
            slot in self._targets
            and self._helper.is_file()
            and self._password.is_file()
        )

    def active(self, slot: str) -> bool:
        """Return whether the slot owns a starting or connected SSH process."""
        return slot in self._processes

    def failed(self, slot: str) -> bool:
        """Return whether a previous SSH attempt ended unsuccessfully."""
        return slot in self._failed

    def toggle(self, slot: str) -> None:
        """Start or stop only the selected slot and discard SSH output."""
        if slot in self._processes:
            self._processes.pop(slot).kill()
            self.changed.emit(slot)
            return
        if not self.available(slot) or not self._ssh:
            return
        self._failed.discard(slot)
        process = QProcess(self)
        self._processes[slot] = process
        env = QProcessEnvironment.systemEnvironment()
        env.insert('SSH_ASKPASS', str(self._helper))
        env.insert('SSH_ASKPASS_REQUIRE', 'force')
        env.insert('AMO_FMS_CAMERA_PASSWORD_FILE', str(self._password))
        env.insert('LC_ALL', 'C')
        process.setProcessEnvironment(env)
        process.setStandardInputFile(QProcess.nullDevice())
        process.setStandardOutputFile(QProcess.nullDevice())
        process.setStandardErrorFile(QProcess.nullDevice())
        process.finished.connect(
            lambda code, _status: self._ended(slot, process, code != 0)
        )
        process.errorOccurred.connect(
            lambda error: self._ended(slot, process, True)
            if error == QProcess.ProcessError.FailedToStart
            else None
        )
        process.start(self._ssh, self._targets[slot].ssh_arguments())
        self.changed.emit(slot)

    def _ended(self, slot: str, process: QProcess, failed: bool) -> None:
        if self._processes.get(slot) is process:
            del self._processes[slot]
            if failed:
                self._failed.add(slot)
            self.changed.emit(slot)
        process.deleteLater()
