"""Keep reported settings separate from missing dispatch assessments."""

from unittest import TestCase

from amo_fms.i18n import Text
from amo_fms.models import Vehicle
from amo_fms.vehicle_details import vehicle_details


class VehicleDetailsTests(TestCase):
    """Exercise the fields that feed the operator's selected-vehicle panel."""

    def test_enabled_setting_does_not_make_charging_vehicle_eligible(self) -> None:
        for status, connection in [('CHARGING', 'CONNECTED'), ('IDLE', 'DISCONNECTED')]:
            with self.subTest(status=status, connection=connection):
                vehicle = Vehicle.parse(
                    {
                        'id': '1',
                        'vehicleNo': 'PINKY-01',
                        'status': status,
                        'connection': connection,
                        'dispatchEnabled': True,
                        'sample': {
                            'epoch': 'fixture',
                            'sequence': 1,
                            'receivedAt': '2026-11-25T23:00:00Z',
                        },
                    }
                )
                details = vehicle_details(vehicle, (), Text('en'))
                self.assertEqual(details['dispatch_setting'], 'Enabled')
                self.assertEqual(details['dispatch_eligibility'], 'Unknown')
                self.assertEqual(details['observation_received_at'], '11-26 08:00:00')
