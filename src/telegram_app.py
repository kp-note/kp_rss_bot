from __future__ import annotations

import asyncio
import logging

import feedparser
from telegram import Update
from telegram.ext import Application, CallbackContext, CommandHandler

from .db import Database
from .feed_worker import FeedWorker

logger = logging.getLogger(__name__)


def build_application(
    token: str,
    db: Database,
    worker: FeedWorker,
    poll_interval_minutes: int,
    admin_user_ids: set[int],
) -> Application:
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("add", _wrap_admin(add_feed, admin_user_ids)))
    app.add_handler(CommandHandler("list", _wrap_admin(list_feeds, admin_user_ids)))
    app.add_handler(CommandHandler("remove", _wrap_admin(remove_feed, admin_user_ids)))
    app.add_handler(CommandHandler("pause", _wrap_admin(pause_feed, admin_user_ids)))
    app.add_handler(CommandHandler("resume", _wrap_admin(resume_feed, admin_user_ids)))
    app.add_handler(CommandHandler("runonce", _wrap_admin(run_once, admin_user_ids)))

    app.bot_data["db"] = db
    app.bot_data["worker"] = worker

    jq = app.job_queue
    jq.run_repeating(_poll_job, interval=poll_interval_minutes * 60, first=10)
    return app


def _wrap_admin(handler, admin_user_ids: set[int]):
    async def wrapped(update: Update, context: CallbackContext):
        if admin_user_ids:
            user = update.effective_user
            if not user or user.id not in admin_user_ids:
                await update.message.reply_text("권한이 없습니다.")
                return
        await handler(update, context)

    return wrapped


async def add_feed(update: Update, context: CallbackContext) -> None:
    db: Database = context.application.bot_data["db"]
    if not context.args:
        await update.message.reply_text("사용법: /add <rss_or_atom_url>")
        return
    url = context.args[0].strip()

    await update.message.reply_text("피드 확인 중...")
    parsed = await asyncio.to_thread(feedparser.parse, url)
    entry_count = len(parsed.entries)
    feed_title = parsed.feed.get("title", "")

    if not entry_count and not feed_title:
        await update.message.reply_text(
            f"❌ 유효한 RSS/Atom 피드를 찾을 수 없습니다.\n"
            f"일반 웹페이지 URL 대신 피드 URL을 입력해주세요.\n"
            f"예) https://example.com/feed 또는 https://example.com/rss"
        )
        return

    try:
        feed_id = db.add_feed(url)
        title_info = f" ({feed_title})" if feed_title else ""
        await update.message.reply_text(
            f"✅ 추가 완료{title_info}\nid={feed_id}, 항목 {entry_count}개 확인됨"
        )
    except Exception as e:
        await update.message.reply_text(f"추가 실패: {e}")


async def list_feeds(update: Update, context: CallbackContext) -> None:
    db: Database = context.application.bot_data["db"]
    feeds = db.list_feeds()
    if not feeds:
        await update.message.reply_text("등록된 피드가 없습니다.")
        return
    lines = []
    for f in feeds:
        status = "paused" if f.paused else "active"
        lines.append(f"{f.id}. [{status}] {f.url}")
    await update.message.reply_text("\n".join(lines))


async def remove_feed(update: Update, context: CallbackContext) -> None:
    db: Database = context.application.bot_data["db"]
    if not context.args:
        await update.message.reply_text("사용법: /remove <id|url>")
        return
    feed_id = _resolve_feed_id(db, context.args[0])
    if feed_id is None:
        await update.message.reply_text("해당 id/url을 찾을 수 없습니다.")
        return
    ok = db.remove_feed(feed_id)
    await update.message.reply_text("삭제 완료" if ok else "해당 id를 찾을 수 없습니다.")


async def pause_feed(update: Update, context: CallbackContext) -> None:
    db: Database = context.application.bot_data["db"]
    if not context.args:
        await update.message.reply_text("사용법: /pause <id|url>")
        return
    feed_id = _resolve_feed_id(db, context.args[0])
    if feed_id is None:
        await update.message.reply_text("해당 id/url을 찾을 수 없습니다.")
        return
    ok = db.set_paused(feed_id, True)
    await update.message.reply_text("일시중지 완료" if ok else "해당 id를 찾을 수 없습니다.")


async def resume_feed(update: Update, context: CallbackContext) -> None:
    db: Database = context.application.bot_data["db"]
    if not context.args:
        await update.message.reply_text("사용법: /resume <id|url>")
        return
    feed_id = _resolve_feed_id(db, context.args[0])
    if feed_id is None:
        await update.message.reply_text("해당 id/url을 찾을 수 없습니다.")
        return
    ok = db.set_paused(feed_id, False)
    await update.message.reply_text("재개 완료" if ok else "해당 id를 찾을 수 없습니다.")


async def run_once(update: Update, context: CallbackContext) -> None:
    worker: FeedWorker = context.application.bot_data["worker"]
    await update.message.reply_text("수집을 1회 실행합니다.")
    await worker.run_once()
    await update.message.reply_text("실행 완료")


async def _poll_job(context: CallbackContext) -> None:
    worker: FeedWorker = context.application.bot_data["worker"]
    try:
        await worker.run_once()
    except Exception:
        logger.exception("Polling job failed")


def _resolve_feed_id(db: Database, value: str) -> int | None:
    raw = value.strip()
    try:
        return int(raw)
    except ValueError:
        pass
    for feed in db.list_feeds():
        if feed.url.strip() == raw:
            return feed.id
    return None
