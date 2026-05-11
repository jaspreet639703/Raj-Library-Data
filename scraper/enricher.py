"""
enricher.py — Visit a library's website and extract:
  email, Instagram handle, Facebook page, YouTube channel
"""

import re
import httpx
from bs4 import BeautifulSoup


TIMEOUT = 10
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


async def enrich_from_website(url: str) -> dict:
    """Fetch the website and return email + social handles."""
    result = {
        "email": "",
        "instagram": "",
        "facebook": "",
        "youtube": "",
        "owner_name": "",
    }

    if not url or not url.startswith("http"):
        return result

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=TIMEOUT,
            headers=HEADERS,
            verify=False,
        ) as client:
            resp = await client.get(url)
            html = resp.text
    except Exception:
        return result

    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(separator=" ")
    full_html = str(soup)

    # ── Email ──────────────────────────────────────────────────────────────
    email_pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    emails = re.findall(email_pattern, text)
    # Filter out common false positives
    ignore = {"sentry", "example", "yourdomain", "test@", "email@"}
    valid_emails = [e for e in emails if not any(x in e.lower() for x in ignore)]
    if valid_emails:
        result["email"] = valid_emails[0]

    # ── Instagram ─────────────────────────────────────────────────────────
    ig_patterns = [
        r'instagram\.com/([A-Za-z0-9_.]{2,30})/?["\'\s<]',
        r'@([A-Za-z0-9_.]{2,30})\s+on\s+instagram',
    ]
    for pat in ig_patterns:
        m = re.search(pat, full_html, re.IGNORECASE)
        if m:
            handle = m.group(1).strip("/")
            if handle.lower() not in {"p", "reel", "stories", "explore", "accounts"}:
                result["instagram"] = handle
                break

    # ── Facebook ──────────────────────────────────────────────────────────
    fb_patterns = [
        r'facebook\.com/([A-Za-z0-9_.]+)/?["\'\s<]',
        r'fb\.com/([A-Za-z0-9_.]+)',
    ]
    for pat in fb_patterns:
        m = re.search(pat, full_html, re.IGNORECASE)
        if m:
            page_id = m.group(1).strip("/")
            if page_id.lower() not in {"sharer", "share", "login", "dialog", "groups"}:
                result["facebook"] = page_id
                break

    # ── YouTube ───────────────────────────────────────────────────────────
    yt_patterns = [
        r'youtube\.com/(@[A-Za-z0-9_.-]+)',
        r'youtube\.com/channel/([A-Za-z0-9_-]+)',
        r'youtube\.com/c/([A-Za-z0-9_-]+)',
        r'youtube\.com/user/([A-Za-z0-9_-]+)',
    ]
    for pat in yt_patterns:
        m = re.search(pat, full_html, re.IGNORECASE)
        if m:
            result["youtube"] = m.group(1)
            break

    # ── Owner / Contact name (heuristic) ─────────────────────────────────
    owner_patterns = [
        r'(?:owner|proprietor|director|founder|managed by)[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)',
        r'(?:Mr\.|Mrs\.|Dr\.|Shri|Smt\.)\s+([A-Z][a-z]+(?: [A-Z][a-z]+)+)',
    ]
    for pat in owner_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            result["owner_name"] = m.group(1).strip()
            break

    return result
