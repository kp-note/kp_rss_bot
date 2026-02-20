from __future__ import annotations

import asyncio
import html
import logging
from dataclasses import dataclass

import feedparser
from telegram import Bot

from .content import extract_main_text, fetch_html, is_probably_paid_substack, is_substack_url
from .db import Database, Feed
from .summarizer import Summarizer
from .time_utils import is_in_quiet_hours

logger = logging.getLogger(__name__)


@dataclass
class WorkerConfig:
    channel_id: str
    quiet_start_hour: int
    quiet_end_hour: int


class FeedWorker:
    def __init__(self, db: Database, bot: Bot, summarizer: Summarizer, config: WorkerConfig):
        self.db = db
        self.bot = bot
        self.summarizer = summarizer
        self.config = config

    async def run_once(self) -> None:
        if is_in_quiet_hours(self.config.quiet_start_hour, self.config.quiet_end_hour):
            logger.info("Quiet hours: skip feed polling.")
            return

        feeds = self.db.active_feeds()
        for feed in feeds:
            await self._process_feed(feed)

    async def _process_feed(self, feed: Feed) -> None:
        parsed = feedparser.parse(feed.url)
        if parsed.bozo:
            logger.warning("Feed fetch failed [%s]: %s", feed.url, parsed.get("bozo_exception", "unknown error"))
        entries = parsed.entries or []
        logger.info("Feed [%s]: %d entries fetched", feed.url, len(entries))
        # Feeds are newest-first. Collect unseen entries, take up to 10 newest,
        # then process oldest-first so notifications arrive in chronological order.
        candidates: list[tuple[str, dict]] = []
        for entry in entries:
            uid = str(entry.get("id") or entry.get("link") or entry.get("title") or "").strip()
            if not uid:
                continue
            if self.db.seen_entry(feed.id, uid):
                continue
            candidates.append((uid, entry))
        for uid, entry in reversed(candidates[:10]):
            sent = await self._handle_entry(entry)
            if sent:
                self.db.mark_entry_seen(feed.id, uid)

    async def _handle_entry(self, entry: dict) -> bool:
        title = str(entry.get("title") or "Untitled")
        link = str(entry.get("link") or "")
        if not link:
            return False

        logger.info("Processing entry: %s", title)
        html_doc = await asyncio.to_thread(fetch_html, link)

        if is_substack_url(link) and is_probably_paid_substack(title, link, html_doc):
            logger.info("Skipping paid/suspected-paid Substack post: %s", title)
            return True

        main_text = await asyncio.to_thread(extract_main_text, link, html_doc)
        if not main_text:
            logger.warning("Failed to extract text from: %s", link)
            text = f"<b>{html.escape(title)}</b>\nFailed to extract article text. Link: {html.escape(link)}"
            await self._send(text)
            return True

        summary = await asyncio.to_thread(self.summarizer.summarize_ko, title, link, main_text)
        if not summary:
            logger.warning("Summarizer returned nothing for: %s", title)
            return False
        msg = f"<b>{html.escape(title)}</b>\n{html.escape(link)}\n\n{html.escape(summary)}"
        await self._send(msg)
        return True

    async def _send(self, text: str) -> None:
        max_len = 3900
        safe_text = text if len(text) <= max_len else text[:max_len] + "\n\n(Truncated due to message length)"
        await self.bot.send_message(chat_id=self.config.channel_id, text=safe_text, parse_mode="HTML")

