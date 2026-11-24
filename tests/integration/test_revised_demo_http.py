"""Verify the revised fare and route flow through the local Web gateway."""

from __future__ import annotations

from typing import cast

from demo_ride_case import DemoRideCase


class RevisedDemoHttpTest(DemoRideCase):
    """Exercise authenticated changes and trip settlement without moving hardware."""

    def test_prepayment_replay_dispatch_alight_and_receipt(self) -> None:
        self.assertEqual(self.observe('ASSIGN')[1]['code'], 'FARE_PREPAYMENT_REQUIRED')
        self.assertEqual(self.http.send(self.ride + '/fare', self.operator)[0], 403)
        self.assertEqual(
            self.http.send(self.observations, self.operator, {'step': 'ASSIGN'})[0], 403
        )
        quote = self.pay_initial()
        for step in ('ASSIGN', 'PICKUP_STOP', 'BOARD', 'DEPART'):
            status, observed = self.observe(step)
            self.assertEqual(status, 200, observed)
        self.assertEqual(self.observe('ALIGHT')[1]['code'], 'DEMO_STEP_OUT_OF_ORDER')
        totals: dict[str, object] = {'distanceMeters': 2.25, 'elapsedSeconds': 17}
        self.assertEqual(self.observe('DESTINATION_STOP', totals)[0], 200)
        self.assertEqual(
            self.observe('DESTINATION_STOP', {**totals, 'elapsedSeconds': 18})[1][
                'code'
            ],
            'DEMO_OBSERVATION_CONFLICT',
        )
        status, closed = self.observe('ALIGHT')
        self.assertEqual(status, 200, closed)
        self.assertEqual((status, closed), self.observe('ALIGHT'))
        self.assertEqual(closed['status'], 'COMPLETED')
        receipt = cast(dict[str, object], closed['receipt'])
        self.assertEqual(receipt['amountMinor'], quote['amountMinor'])
        self.assertEqual(receipt['quoteId'], quote['id'])
        self.assertEqual(
            self.http.send(self.ride + '/fare', self.passenger)[1]['receipt'], receipt
        )

    def test_route_acceptance_application_and_restart_are_distinct(self) -> None:
        self.pay_initial()
        self.depart()
        self.assertEqual(self.observe('STOP_WAIT')[0], 200)
        proposal = self.propose('S4')
        revision = {'revisionId': proposal['revisionId']}
        self.assertGreater(int(str(proposal['deltaMinor'])), 0)
        self.assertEqual(
            self.route('issue', revision)[1]['code'],
            'DEMO_CHANGE_ACCEPTANCE_OR_PAYMENT_REQUIRED',
        )
        paid = self.accept_change(proposal)
        self.assertEqual(paid['paymentStatus'], 'SUCCEEDED')
        self.assertEqual(paid['effectiveDestination'], 'S2')
        status, scope = self.route('issue', revision)
        self.assertEqual(status, 200, scope)
        self.assertEqual(self.route('issue', revision), (status, scope))
        self.assertEqual(
            self.route('report', {**scope, 'report': 'APPLIED'})[1]['code'],
            'DEMO_ROUTE_REPORT_OUT_OF_ORDER',
        )
        self.assertEqual(
            self.route('report', {**scope, 'report': 'ACKNOWLEDGED'})[0], 200
        )
        self.assertEqual(
            self.observe('REDEPART')[1]['code'],
            'DEMO_APPLIED_CHANGE_REQUIRED_FOR_REDEPARTURE',
        )
        applied = {**scope, 'report': 'APPLIED'}
        self.assertEqual(
            self.route('report', {**applied, 'epoch': 'prior-session'})[1]['code'],
            'DEMO_ROUTE_SCOPE_MISMATCH',
        )
        result = self.route('report', applied)
        self.assertEqual(result[0], 200, result[1])
        self.assertEqual(self.route('report', applied), result)
        self.assertEqual(
            self.http.send(self.ride + '/route-change', self.passenger)[1][
                'effectiveDestination'
            ],
            'S4',
        )
        self.assertEqual(self.observe('REDEPART')[0], 200)
        receipt = self.finish()
        self.assertEqual(
            receipt['quoteId'], cast(dict[str, object], proposal['quote'])['id']
        )

    def test_paid_failed_change_keeps_original_fare(self) -> None:
        initial = self.pay_initial()
        self.depart()
        proposal = self.propose('S4')
        self.assertEqual(self.accept_change(proposal)['paymentStatus'], 'SUCCEEDED')
        status, scope = self.route('issue', {'revisionId': proposal['revisionId']})
        self.assertEqual(status, 200, scope)
        self.assertEqual(self.route('report', {**scope, 'report': 'FAILED'})[0], 200)
        status, change = self.http.send(self.ride + '/route-change', self.passenger)
        self.assertEqual(status, 200, change)
        self.assertEqual(change['effectiveDestination'], 'S2')
        self.assertEqual(change['status'], 'FAILED')
        self.assertEqual(change['paymentStatus'], 'SUCCEEDED')
        self.assertEqual(self.finish()['quoteId'], initial['id'])
