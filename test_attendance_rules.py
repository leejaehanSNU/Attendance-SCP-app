import unittest
from datetime import datetime

import pytz

from attendance_rules import (
    UNAUTHORIZED_ABSENT,
    UNAUTHORIZED_LATE,
    UNAUTHORIZED_OUT,
    has_real_attendance,
    is_workday,
    unauthorized_status_for,
    work_dates_to_close,
)


class UnauthorizedStatusTests(unittest.TestCase):
    def test_complete_normal_day_needs_no_automatic_record(self):
        self.assertIsNone(unauthorized_status_for(['\ucd9c\uadfc', '\ud1f4\uadfc']))
        self.assertIsNone(unauthorized_status_for(['\uc9c0\uac01', '\uc870\ud1f4']))

    def test_missing_records_become_absent(self):
        self.assertEqual(unauthorized_status_for([]), UNAUTHORIZED_ABSENT)

    def test_missing_checkout_becomes_unauthorized_checkout(self):
        self.assertEqual(unauthorized_status_for(['\ucd9c\uadfc']), UNAUTHORIZED_OUT)

    def test_checkout_without_clock_in_becomes_unauthorized_late(self):
        self.assertEqual(unauthorized_status_for(['\ud1f4\uadfc']), UNAUTHORIZED_LATE)

    def test_manual_absence_and_existing_auto_rows_are_idempotent(self):
        self.assertIsNone(unauthorized_status_for(['\uacb0\uadfc']))
        self.assertIsNone(unauthorized_status_for([UNAUTHORIZED_ABSENT]))
        self.assertIsNone(unauthorized_status_for(['\ucd9c\uadfc', UNAUTHORIZED_OUT]))


class WorkDateTests(unittest.TestCase):
    def setUp(self):
        self.kst = pytz.timezone('Asia/Seoul')

    def test_current_day_is_not_closed_at_18(self):
        now = self.kst.localize(datetime(2026, 8, 24, 18, 30))
        self.assertNotIn('2026-08-24', [date.isoformat() for date in work_dates_to_close(now)])

    def test_current_day_is_closed_at_2359(self):
        now = self.kst.localize(datetime(2026, 8, 24, 23, 59))
        self.assertIn('2026-08-24', [date.isoformat() for date in work_dates_to_close(now)])

    def test_public_holiday_is_not_closed(self):
        now = self.kst.localize(datetime(2026, 10, 7, 9, 0))
        dates = [date.isoformat() for date in work_dates_to_close(now)]
        self.assertEqual(dates, ['2026-10-01', '2026-10-02', '2026-10-06'])
        self.assertFalse(is_workday(datetime(2026, 10, 5).date()))

    def test_only_days_with_real_activity_are_eligible_for_auto_records(self):
        self.assertTrue(has_real_attendance(['\ucd9c\uadfc']))
        self.assertTrue(has_real_attendance(['\uacb0\uadfc']))
        self.assertFalse(has_real_attendance([]))
        self.assertFalse(has_real_attendance([UNAUTHORIZED_ABSENT]))


if __name__ == '__main__':
    unittest.main()
