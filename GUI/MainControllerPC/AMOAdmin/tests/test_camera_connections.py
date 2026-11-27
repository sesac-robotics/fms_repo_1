"""Check per-slot SSH launch and password delivery without using a device."""

import os
import sys
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from PyQt6.QtWidgets import QApplication

from amo_fms.camera_connections import CameraConnections, CameraTarget
from amo_fms.i18n import Text
from amo_fms.models import Vehicle
from amo_fms.preview_panel import PreviewPanel


class CameraConnectionTest(TestCase):
    def test_button_launches_only_its_configured_slot(self) -> None:
        app = QApplication.instance() or QApplication([])
        app.processEvents()
        with TemporaryDirectory() as directory:
            panel = PreviewPanel(Text('en'), lambda _: None, local_directory=directory)
            fleet = tuple(
                Vehicle.parse({'id': index, 'vehicleNo': f'PINKY-{index:02d}'})
                for index in range(1, 5)
            )
            panel.present(fleet, '1')
            self.assertFalse(
                any(button.isEnabled() for button in panel._buttons.values())
            )
            with (
                patch.object(CameraConnections, 'available', return_value=True),
                patch.object(CameraConnections, 'toggle', autospec=True) as toggle,
            ):
                panel.present(fleet, '1')
                for vehicle in fleet:
                    button = panel._buttons[vehicle.number]
                    self.assertTrue(button.isEnabled())
                    button.click()
                self.assertEqual(
                    [call.args[1] for call in toggle.call_args_list],
                    [vehicle.number for vehicle in fleet],
                )
            panel.close()

    def test_camera_target_limits_ssh_to_a_fixed_capture_command(self) -> None:
        target = CameraTarget.parse(
            {
                'destination': 'operator@camera.test',
                'robot_id': 'camera_02',
                'setup': '/opt/camera setup.bash',
            }
        )
        arguments = target.ssh_arguments()
        self.assertIn('StrictHostKeyChecking=yes', arguments)
        self.assertEqual(arguments[-2], 'operator@camera.test')
        self.assertIn(
            'amo_camera_streamer camera_streamer --robot-id camera_02', arguments[-1]
        )
        with self.assertRaises(ValueError):
            CameraTarget.parse(
                {
                    'destination': '-oProxyCommand=x',
                    'robot_id': 'camera_02',
                    'setup': '/tmp/setup',
                }
            )

    def test_askpass_only_accepts_owner_private_password_files(self) -> None:
        with TemporaryDirectory() as directory:
            credential = Path(directory) / 'test-password'
            credential.write_text('mock-only\n')
            credential.chmod(0o600)
            env = dict(os.environ, AMO_FMS_CAMERA_PASSWORD_FILE=str(credential))
            env.pop('SSH_ASKPASS_PROMPT', None)
            invocation = [
                sys.executable,
                '-c',
                'from amo_fms.camera_askpass import main; raise SystemExit(main())',
            ]
            result = run(
                [*invocation, 'Password:'], capture_output=True, env=env, check=True
            )
            self.assertEqual(result.stdout, b'mock-only\n')
            result = run(
                [*invocation, 'Continue connecting?'],
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, b'')
            credential.chmod(0o644)
            result = run(
                [*invocation, 'Password:'], capture_output=True, env=env, check=False
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, b'')
