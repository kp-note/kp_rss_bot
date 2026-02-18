from datetime import datetime
from zoneinfo import ZoneInfo
import unittest

from src.time_utils import is_in_quiet_hours


class QuietHourTests(unittest.TestCase):
    def test_cross_midnight_quiet_hours(self):
        kst = ZoneInfo("Asia/Seoul")
        self.assertTrue(is_in_quiet_hours(23, 8, datetime(2026, 2, 15, 23, 10, tzinfo=kst)))
        self.assertTrue(is_in_quiet_hours(23, 8, datetime(2026, 2, 16, 7, 59, tzinfo=kst)))
        self.assertFalse(is_in_quiet_hours(23, 8, datetime(2026, 2, 16, 8, 0, tzinfo=kst)))
        self.assertFalse(is_in_quiet_hours(23, 8, datetime(2026, 2, 16, 12, 0, tzinfo=kst)))


if __name__ == "__main__":
    unittest.main()

