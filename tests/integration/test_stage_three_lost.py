"""Execute SD-12 report scope, delivery, retries and correction without images."""

import unittest
from dataclasses import replace

from stage_three_lost import Detection, Finding, LostProperty, Recipient, Snapshot
from stage_two_vehicle import Scope

SCOPE = Scope('taxi-1', 'assignment-3', 'vehicle-3', 2)
BEFORE = Snapshot(SCOPE, 'before', 99)
AFTER = Snapshot(SCOPE, 'after', 101)
CANDIDATE = Detection(SCOPE, 'detection-1', 102, Finding.CANDIDATE, BEFORE, AFTER)


def service() -> LostProperty:
    """Return a fixture with registered recipients and a confirmed alighting tick."""
    return LostProperty(SCOPE, 'rider-1', 'operator-1', 100)


class LostPropertyTest(unittest.TestCase):
    """Check targeting and evidence boundaries using opaque fixture snapshot IDs."""

    def test_sd12_candidate_notifies_only_ride_user_and_admin(self) -> None:
        ledger = service()
        result = ledger.accept(CANDIDATE)
        assert result is not None
        self.assertIs(result.finding, Finding.CANDIDATE)
        self.assertEqual(
            ledger.pending(CANDIDATE.key),
            {Recipient.RIDER: 'rider-1', Recipient.ADMIN: 'operator-1'},
        )
        self.assertFalse(
            ledger.record_delivery(
                CANDIDATE.key, Recipient.RIDER, 'other', 103, success=True
            )
        )
        self.assertFalse(
            ledger.record_delivery(
                CANDIDATE.key, Recipient.ADMIN, 'operator-1', 101, success=True
            )
        )
        self.assertEqual(result.success_at, {})

    def test_sd12_no_detection_and_unavailable_are_distinct_and_silent(self) -> None:
        ledger = service()
        for finding in (Finding.NONE, Finding.UNAVAILABLE):
            item = replace(CANDIDATE, key=finding.value, finding=finding)
            result = ledger.accept(item)
            assert result is not None
            self.assertIs(result.finding, finding)
            self.assertEqual(ledger.pending(item.key), {})

    def test_sd12_missing_wrong_ride_and_unordered_snapshots_cannot_alert(self) -> None:
        ledger = service()
        invalid_after = (
            None,
            replace(AFTER, scope=replace(SCOPE, trip='other')),
            replace(AFTER, scope=replace(SCOPE, vehicle='other')),
            replace(AFTER, captured=100),
            replace(AFTER, captured=103),
            replace(AFTER, key=BEFORE.key),
        )
        for index, after in enumerate(invalid_after):
            item = replace(CANDIDATE, key=f'bad-{index}', after=after)
            result = ledger.accept(item)
            assert result is not None
            self.assertIs(result.finding, Finding.UNAVAILABLE)
            self.assertEqual(ledger.pending(item.key), {})

    def test_sd12_rejects_foreign_result_and_preserves_first_detection(self) -> None:
        ledger = service()
        self.assertIsNone(
            ledger.accept(replace(CANDIDATE, scope=replace(SCOPE, epoch=1)))
        )
        self.assertIsNone(ledger.accept(replace(CANDIDATE, observed=99)))
        self.assertIsNone(ledger.accept(replace(CANDIDATE, key='')))
        result = ledger.accept(CANDIDATE)
        assert result is not None
        self.assertIs(ledger.accept(CANDIDATE), result)
        self.assertIsNone(ledger.accept(replace(CANDIDATE, finding=Finding.NONE)))
        self.assertIs(ledger.accept(CANDIDATE), result)

    def test_sd12_only_the_failed_target_retries_and_success_times_stay_first(
        self,
    ) -> None:
        ledger = service()
        item = ledger.accept(CANDIDATE)
        assert item is not None
        key = CANDIDATE.key
        self.assertTrue(
            ledger.record_delivery(key, Recipient.RIDER, 'rider-1', 103, success=True)
        )
        self.assertTrue(
            ledger.record_delivery(
                key, Recipient.ADMIN, 'operator-1', 104, success=False
            )
        )
        self.assertEqual(ledger.pending(key), {Recipient.ADMIN: 'operator-1'})
        self.assertFalse(
            ledger.record_delivery(
                key, Recipient.ADMIN, 'operator-1', 104, success=True
            )
        )
        self.assertFalse(
            ledger.record_delivery(key, Recipient.RIDER, 'rider-1', 105, success=True)
        )
        self.assertTrue(
            ledger.record_delivery(
                key, Recipient.ADMIN, 'operator-1', 106, success=True
            )
        )
        self.assertEqual(item.success_at, {Recipient.RIDER: 103, Recipient.ADMIN: 106})
        self.assertIs(ledger.accept(CANDIDATE), item)
        self.assertEqual(ledger.pending(key), {})

    def test_sd12_false_positive_correction_retains_audit_and_holds_pending_retry(
        self,
    ) -> None:
        ledger = service()
        item = ledger.accept(CANDIDATE)
        assert item is not None
        key = CANDIDATE.key
        self.assertTrue(
            ledger.record_delivery(
                key, Recipient.ADMIN, 'operator-1', 103, success=True
            )
        )
        self.assertFalse(ledger.correct(key, 'other', 104, 'manual review'))
        self.assertFalse(ledger.correct(key, 'operator-1', 101, 'stale review'))
        self.assertTrue(ledger.correct(key, 'operator-1', 104, 'manual review'))
        self.assertFalse(ledger.correct(key, 'operator-1', 105, 'duplicate'))
        self.assertEqual(item.success_at, {Recipient.ADMIN: 103})
        self.assertEqual(item.corrections, [(104, 'manual review')])
        self.assertEqual(ledger.pending(key), {})
        self.assertFalse(
            ledger.record_delivery(key, Recipient.RIDER, 'rider-1', 106, success=True)
        )
