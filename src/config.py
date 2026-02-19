from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    telegram_channel_id: str
    admin_user_ids: set[int]
    default_summary_provider: str
    gemini_api_key: str
    gemini_model: str
    openai_api_key: str
    openai_model: str
    database_path: Path
    poll_interval_minutes: int
    quiet_start_hour: int
    quiet_end_hour: int
    seed_feed_urls: list[str]


def _parse_seed_feeds(raw: str) -> list[str]:
    return [u.strip() for u in raw.split(",") if u.strip()]


def _parse_admin_ids(raw: str) -> set[int]:
    result: set[int] = set()
    if not raw.strip():
        return result
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        result.add(int(part))
    return result


def load_settings() -> Settings:
    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    channel = os.getenv("TELEGRAM_CHANNEL_ID", "").strip()
    if not token or not channel:
        raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID are required.")

    db_path = Path(os.getenv("DATABASE_PATH", "./data/rss_bot.db")).resolve()

    return Settings(
        telegram_bot_token=token,
        telegram_channel_id=channel,
        admin_user_ids=_parse_admin_ids(os.getenv("ADMIN_USER_IDS", "")),
        default_summary_provider=os.getenv("DEFAULT_SUMMARY_PROVIDER", "gemini").strip().lower(),
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip(),
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip(),
        database_path=db_path,
        poll_interval_minutes=int(os.getenv("POLL_INTERVAL_MINUTES", "60")),
        quiet_start_hour=int(os.getenv("QUIET_START_HOUR", "23")),
        quiet_end_hour=int(os.getenv("QUIET_END_HOUR", "8")),
        seed_feed_urls=_parse_seed_feeds(os.getenv("SEED_FEEDS", "")),
    )

