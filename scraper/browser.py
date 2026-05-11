"""
browser.py — Playwright-based Google Maps scraper
Extracts library listings for a given tehsil + entity type.
"""

import asyncio
import random
import re
from playwright.async_api import async_playwright
from scraper.enricher import enrich_from_website


async def scrape_libraries_in_tehsil(state: str, district: str, tehsil: str, entity: str) -> list[dict]:
    """Search Google Maps for `entity` in `tehsil, district, state` and return all results."""

    search_query = f"{entity} in {tehsil}, {district}, {state}"
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        context = await browser.new_context(
            locale="en-US",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        try:
            maps_url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
            await page.goto(maps_url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(random.uniform(3, 6))

            # Scroll the results panel to load all listings
            results_panel = page.locator('div[role="feed"]')
            for _ in range(15):
                await results_panel.evaluate("el => el.scrollBy(0, 800)")
                await asyncio.sleep(random.uniform(1.5, 3.0))

            # Collect all listing cards
            listing_cards = await page.locator('div[role="feed"] > div > div > a').all()
            print(f"    Found {len(listing_cards)} raw listing cards")

            for card in listing_cards:
                try:
                    # Click each card to load detail panel
                    await card.click()
                    await asyncio.sleep(random.uniform(2, 4))

                    record = await _extract_detail_panel(page, state, district, tehsil, entity)
                    if record and record.get("name"):
                        results.append(record)

                except Exception as e:
                    continue

        except Exception as e:
            print(f"    Browser error: {e}")
        finally:
            await browser.close()

    # Deduplicate by name+address within this batch
    seen = set()
    unique = []
    for r in results:
        key = (r.get("name", "").lower().strip(), r.get("address", "").lower().strip())
        if key not in seen:
            seen.add(key)
            unique.append(r)

    return unique


async def _extract_detail_panel(page, state, district, tehsil, entity) -> dict | None:
    """Extract all fields from the right-side detail panel after clicking a listing."""

    record = {
        "state": state,
        "district": district,
        "tehsil": tehsil,
        "entity_type": entity,
        "name": "",
        "owner_name": "",
        "address": "",
        "phone": "",
        "rating": "",
        "website": "",
        "email": "",
        "instagram": "",
        "facebook": "",
        "youtube": "",
        "google_maps_url": page.url,
        "place_id": _extract_place_id(page.url),
    }

    try:
        await page.wait_for_selector('h1.DUwDvf', timeout=8000)
    except Exception:
        return None

    # Name
    try:
        record["name"] = await page.locator('h1.DUwDvf').inner_text()
    except Exception:
        pass

    # Address
    try:
        addr_el = page.locator('[data-item-id="address"]')
        if await addr_el.count() > 0:
            record["address"] = await addr_el.get_attribute("aria-label") or ""
            record["address"] = record["address"].replace("Address: ", "").strip()
    except Exception:
        pass

    # Phone
    try:
        phone_el = page.locator('[data-item-id^="phone:tel"]')
        if await phone_el.count() > 0:
            record["phone"] = await phone_el.get_attribute("aria-label") or ""
            record["phone"] = re.sub(r"[^\d+]", "", record["phone"].replace("Phone: ", ""))
    except Exception:
        pass

    # Rating
    try:
        rating_el = page.locator('div.F7nice span[aria-hidden="true"]').first
        if await rating_el.count() > 0:
            record["rating"] = await rating_el.inner_text()
    except Exception:
        pass

    # Website
    try:
        web_el = page.locator('[data-item-id="authority"] a')
        if await web_el.count() > 0:
            record["website"] = await web_el.get_attribute("href") or ""
    except Exception:
        pass

    # Enrich from website (email, instagram, facebook, youtube)
    if record["website"]:
        try:
            enriched = await enrich_from_website(record["website"])
            record.update(enriched)
        except Exception:
            pass

    # Try to find social links directly on Maps listing
    try:
        page_html = await page.content()

        # Instagram
        ig_match = re.search(r'instagram\.com/([A-Za-z0-9_.]+)', page_html)
        if ig_match and not record["instagram"]:
            record["instagram"] = ig_match.group(1)

        # Facebook
        fb_match = re.search(r'facebook\.com/([A-Za-z0-9_.]+)', page_html)
        if fb_match and not record["facebook"]:
            record["facebook"] = fb_match.group(1)

        # YouTube
        yt_match = re.search(r'youtube\.com/@?([A-Za-z0-9_.-]+)', page_html)
        if yt_match and not record["youtube"]:
            record["youtube"] = yt_match.group(1)

    except Exception:
        pass

    return record


def _extract_place_id(url: str) -> str:
    match = re.search(r"place/([^/]+)", url)
    if match:
        return match.group(1)
    cid_match = re.search(r"cid=(\d+)", url)
    if cid_match:
        return cid_match.group(1)
    return url[-40:] if len(url) > 40 else url
