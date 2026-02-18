from __future__ import annotations

import re


def is_substack_url(url: str) -> bool:
    return "substack.com" in url.lower()


def is_probably_paid_substack(entry_title: str, entry_url: str, html: str | None = None) -> bool:
    title = (entry_title or "").lower()
    if any(token in title for token in ("paid", "subscriber", "members-only", "members only")):
        return True

    url_lower = (entry_url or "").lower()
    if "/p/" not in url_lower:
        return False

    if html:
        markers = [
            "this post is for paid subscribers",
            "become a paid subscriber",
            "subscribe to continue reading",
            "paid subscribers",
        ]
        lower_html = html.lower()
        if any(m in lower_html for m in markers):
            return True

        # Heuristic: heavy paywall markup often includes these terms.
        if re.search(r"paywall|subscriber-only|premium", lower_html):
            return True
    return False


def fetch_html(url: str, timeout_seconds: int = 20) -> str | None:
    import httpx

    try:
        resp = httpx.get(url, timeout=timeout_seconds, follow_redirects=True)
        if resp.status_code >= 400:
            return None
        return resp.text
    except Exception:
        return None


def extract_main_text(url: str, html: str | None) -> str:
    import trafilatura

    if not html:
        return ""
    extracted = trafilatura.extract(
        html,
        url=url,
        include_comments=False,
        include_tables=False,
        output_format="txt",
    )
    return (extracted or "").strip()
