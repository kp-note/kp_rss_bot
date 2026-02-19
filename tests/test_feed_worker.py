from __future__ import annotations

import asyncio
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from src.db import Database
from src.feed_worker import FeedWorker, WorkerConfig


def _make_worker(db: Database, sent_messages: list) -> FeedWorker:
    bot = MagicMock()
    bot.send_message = AsyncMock(side_effect=lambda **kw: sent_messages.append(kw["text"]))

    summarizer = MagicMock()
    summarizer.summarize_ko = MagicMock(return_value="요약 내용")

    config = WorkerConfig(channel_id="@test", quiet_start_hour=23, quiet_end_hour=8)
    return FeedWorker(db=db, bot=bot, summarizer=summarizer, config=config)


def _make_db(tmp_path: Path) -> Database:
    return Database(tmp_path / "test.db")


class TestMarkEntrySeenOnlyOnSuccess(unittest.IsolatedAsyncioTestCase):
    async def test_entry_not_marked_seen_when_summarizer_fails(self):
        """요약 실패 시 entry를 seen 처리하지 않아서 다음에 재시도 가능해야 함."""
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            db = _make_db(Path(tmp))
            feed_id = db.add_feed("https://example.com/feed")
            feed = db.active_feeds()[0]

            sent = []
            worker = _make_worker(db, sent)
            worker.summarizer.summarize_ko = MagicMock(return_value=None)  # 요약 실패

            entry = {"id": "uid-1", "title": "Test", "link": "https://example.com/p/test"}
            html_doc = "<html><body>Some article text here</body></html>"

            with patch("src.feed_worker.fetch_html", return_value=html_doc), \
                 patch("src.feed_worker.extract_main_text", return_value="본문 내용"):
                result = await worker._handle_entry(entry)

            self.assertFalse(result)
            self.assertEqual(sent, [])
            # seen 처리되지 않아야 함
            self.assertFalse(db.seen_entry(feed.id, "uid-1"))

    async def test_entry_marked_seen_when_message_sent(self):
        """메시지 전송 성공 시 entry가 seen 처리돼야 함."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            db = _make_db(Path(tmp))
            feed_id = db.add_feed("https://example.com/feed")
            feed = db.active_feeds()[0]

            sent = []
            worker = _make_worker(db, sent)

            entry = {"id": "uid-2", "title": "Test Article", "link": "https://example.com/p/test2"}
            html_doc = "<html><body>Some article text here</body></html>"

            with patch("src.feed_worker.fetch_html", return_value=html_doc), \
                 patch("src.feed_worker.extract_main_text", return_value="본문 내용"):
                result = await worker._handle_entry(entry)

            self.assertTrue(result)
            self.assertEqual(len(sent), 1)


class TestProcessFeedBozoLogging(unittest.IsolatedAsyncioTestCase):
    async def test_bozo_feed_logs_warning_and_skips(self):
        """feedparser bozo(연결 실패 등) 시 경고 로그 후 조용히 스킵해야 함."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            db = _make_db(Path(tmp))
            db.add_feed("https://broken.example.com/feed")
            feed = db.active_feeds()[0]

            sent = []
            worker = _make_worker(db, sent)

            broken_result = MagicMock()
            broken_result.bozo = True
            broken_result.get = lambda k, d=None: Exception("SSL error") if k == "bozo_exception" else d
            broken_result.entries = []

            with patch("src.feed_worker.feedparser.parse", return_value=broken_result), \
                 patch("src.feed_worker.logger") as mock_logger:
                await worker._process_feed(feed)

            mock_logger.warning.assert_called_once()
            self.assertEqual(sent, [])

    async def test_duplicate_entry_not_processed_twice(self):
        """이미 seen 처리된 entry는 다시 처리하지 않아야 함."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            db = _make_db(Path(tmp))
            db.add_feed("https://example.com/feed")
            feed = db.active_feeds()[0]
            db.mark_entry_seen(feed.id, "uid-already-seen")

            sent = []
            worker = _make_worker(db, sent)

            mock_parsed = MagicMock()
            mock_parsed.bozo = False
            mock_parsed.entries = [{"id": "uid-already-seen", "title": "Old", "link": "https://example.com/p/old"}]

            with patch("src.feed_worker.feedparser.parse", return_value=mock_parsed):
                await worker._process_feed(feed)

            self.assertEqual(sent, [])


if __name__ == "__main__":
    unittest.main()
