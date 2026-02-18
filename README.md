# RSS Insight Bot

Telegram bot that monitors RSS/Atom feeds, summarizes free posts in Korean, and posts to a Telegram channel.

## V1 Scope

- Poll feeds every hour
- Skip feed polling during KST quiet hours (23:00-08:00)
- Substack paid/suspected-paid posts: post link only (no summary)
- Telegram commands: `/add`, `/list`, `/remove`, `/pause`, `/resume`
- Local SQLite database for testing
- Gemini as default summarization model (OpenAI optional fallback)

## Quick Start

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create `.env` from `.env.example` and fill values.
4. Start bot:

```bash
python -m src.main
```

## Telegram Setup

- Add the bot as an admin in your channel.
- Set `TELEGRAM_CHANNEL_ID` to channel username like `@KP_blog_RSS` or numeric channel id.
- (Recommended) Set `ADMIN_USER_IDS` to your Telegram numeric user id(s) to lock commands.

## Commands

- `/add <rss_url>`
- `/list`
- `/remove <id|url>`
- `/pause <id|url>`
- `/resume <id|url>`
- `/runonce` (수동 1회 수집)

## Notes

- Feed polling runs every 1 hour.
- During KST 23:00-08:00, polling is skipped.
- Bot commands are still available during quiet hours.
