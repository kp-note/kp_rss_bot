from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.db import Database


class TestEnsureFeed(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self._tmp.name) / "test.db")

    def tearDown(self):
        self._tmp.cleanup()

    def test_ensure_feed_adds_new_url(self):
        """새 URL은 추가되고 True를 반환해야 함."""
        added = self.db.ensure_feed("https://example.com/feed")
        self.assertTrue(added)
        urls = [f.url for f in self.db.list_feeds()]
        self.assertIn("https://example.com/feed", urls)

    def test_ensure_feed_ignores_duplicate(self):
        """이미 존재하는 URL은 무시하고 False를 반환해야 함."""
        self.db.ensure_feed("https://example.com/feed")
        added_again = self.db.ensure_feed("https://example.com/feed")
        self.assertFalse(added_again)
        self.assertEqual(len(self.db.list_feeds()), 1)

    def test_ensure_feed_active_by_default(self):
        """시딩된 피드는 active 상태여야 함."""
        self.db.ensure_feed("https://example.com/feed")
        feeds = self.db.active_feeds()
        self.assertEqual(len(feeds), 1)
        self.assertFalse(feeds[0].paused)

    def test_ensure_feed_does_not_unpause_existing(self):
        """이미 paused된 피드를 ensure_feed가 다시 활성화하지 않아야 함."""
        feed_id = self.db.add_feed("https://example.com/feed")
        self.db.set_paused(feed_id, True)
        self.db.ensure_feed("https://example.com/feed")  # 이미 존재 → 무시
        feeds = self.db.active_feeds()
        self.assertEqual(len(feeds), 0)  # paused 상태 유지


if __name__ == "__main__":
    unittest.main()
