from __future__ import annotations

import logging

from telegram import Bot

from .config import load_settings
from .db import Database
from .feed_worker import FeedWorker, WorkerConfig
from .summarizer import Summarizer, SummaryConfig
from .telegram_app import build_application


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    settings = load_settings()
    db = Database(settings.database_path)

    for url in settings.seed_feed_urls:
        if db.ensure_feed(url):
            logging.getLogger(__name__).info("Seeded feed from SEED_FEEDS: %s", url)

    summarizer = Summarizer(
        SummaryConfig(
            provider=settings.default_summary_provider,
            gemini_api_key=settings.gemini_api_key,
            gemini_model=settings.gemini_model,
            openai_api_key=settings.openai_api_key,
            openai_model=settings.openai_model,
        )
    )

    worker = FeedWorker(
        db=db,
        bot=Bot(token=settings.telegram_bot_token),
        summarizer=summarizer,
        config=WorkerConfig(
            channel_id=settings.telegram_channel_id,
            quiet_start_hour=settings.quiet_start_hour,
            quiet_end_hour=settings.quiet_end_hour,
            lookback_hours=settings.lookback_hours,
        ),
    )

    app = build_application(
        token=settings.telegram_bot_token,
        db=db,
        worker=worker,
        poll_interval_minutes=settings.poll_interval_minutes,
        admin_user_ids=settings.admin_user_ids,
    )

    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()

