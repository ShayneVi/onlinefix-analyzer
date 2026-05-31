"""Scrape freetp.org and sync game links into the database.

Strategy:
  - Scrape all pages of freetp.org/po-seti/ (online-fix guides)
  - Extract a candidate title from each URL slug
  - Try to match that title against existing OFME games in the DB
      1. Exact case-insensitive match
      2. Partial match (our title in DB title, or DB title in ours)
  - If matched:  set freetp_url on the existing row, sources -> 'ofme,freetp'
  - If no match: insert a new freetp-only game (id >= 10_000_000)
"""

import re
import time
import random
import logging
from datetime import datetime, timezone

import requests as req
from bs4 import BeautifulSoup

import config

logger = logging.getLogger(__name__)

BASE = "https://freetp.org"

# Markers that signal the end of the game name in a freetp URL slug.
# These are common Russian/English words that appear after the game title.
_SLUG_CUT_MARKERS = [
    "-igra-po-seti-i-internetu-",
    "-igrat-po-seti-i-internetu-",
    "-igra-po-seti-",
    "-igrat-po-seti-",
    "-po-seti-i-internetu-",
    "-po-lokalnoy-seti-",
    "-igraem-vmeste-",
    "-igraem-",
    "-po-seti-",
    "-rukovodstvo-zapuska-",
    "-rukovodstvo-",
    "-nastroika-",
    "-nastroyki-",
    "-zapusk-",
    "-nastroika-",
    "-v-multiplayer-",
    "-v-multipleer-",
    "-multiplayer-",
    "-multipleer-",
    "-kak-igrat-",
    "-setevoi-",
    "-setevaya-",
    "-lan-v-",
    "-igra-besplatno-",
    "-igra-v-",
    "-igra-online-",
    "-igrat-onlayn-",
    "-igra-s-",
    "-igra-lokalno-",
    "-igra-",
    "-igrat-",
]


def extract_title_from_slug(slug: str) -> str:
    """Best-effort game title from a freetp slug like '2075-stellaris-igra-po-seti...'"""
    # Remove leading numeric ID
    slug = re.sub(r"^\d+-", "", slug)
    lower = slug.lower()

    cut = len(slug)
    for marker in _SLUG_CUT_MARKERS:
        idx = lower.find(marker)
        if 0 < idx < cut:
            cut = idx

    name_part = slug[:cut]
    # Capitalise each word, keep digits as-is
    return " ".join(
        w[0].upper() + w[1:] if w and w[0].isalpha() else w
        for w in name_part.split("-")
        if w
    )


def _fetch(url: str) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
    }
    for attempt in range(1, 4):
        try:
            resp = req.get(url, headers=headers, timeout=20)
            if resp.status_code == 200:
                return resp.text
            logger.warning("Status %d for %s (attempt %d)", resp.status_code, url, attempt)
        except Exception as exc:
            logger.warning("Fetch failed (attempt %d): %s", attempt, exc)
        time.sleep(2 ** attempt)
    logger.error("Failed to fetch %s after 3 attempts", url)
    return ""


def _detect_max_page() -> int:
    html = _fetch(BASE)
    if not html:
        return 0
    soup = BeautifulSoup(html, "lxml")
    max_page = 0
    for a in soup.find_all("a", href=True):
        if "/page/" in a["href"]:
            try:
                n = int(a["href"].strip("/").split("/")[-1])
                if n > max_page:
                    max_page = n
            except ValueError:
                pass
    return max_page


def scrape_freetp_page(page_num: int) -> list[dict]:
    """Return list of {title, freetp_url, slug} dicts from one page."""
    url = f"{BASE}/page/{page_num}/"
    html = _fetch(url)
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    results = []
    seen: set[str] = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/po-seti/" not in href or "#" in href or not href.endswith(".html"):
            continue
        freetp_url = href if href.startswith("http") else BASE + href
        # Skip bare category root
        if freetp_url == BASE + "/po-seti/":
            continue
        if freetp_url in seen:
            continue
        seen.add(freetp_url)

        slug = freetp_url.rstrip("/").split("/")[-1]
        if slug.endswith(".html"):
            slug = slug[:-5]

        title = extract_title_from_slug(slug)
        if title:
            results.append({"title": title, "freetp_url": freetp_url, "slug": slug})

    return results


def _upsert_freetp_game(conn, g: dict):
    """Match game to existing OFME entry or insert as freetp-only."""
    freetp_url = g["freetp_url"]
    title = g["title"]

    # Already linked?
    existing = conn.execute(
        "SELECT id FROM games WHERE freetp_url = ?", (freetp_url,)
    ).fetchone()
    if existing:
        return

    now = datetime.now(timezone.utc).isoformat()

    # 1. Exact title match (case-insensitive)
    match = conn.execute(
        "SELECT id FROM games WHERE LOWER(title) = LOWER(?) AND (sources IS NULL OR sources='ofme') LIMIT 1",
        (title,),
    ).fetchone()

    # 2. Partial match — only if title is at least 5 chars to avoid false positives
    if not match and len(title) >= 5:
        match = conn.execute(
            """
            SELECT id FROM games
            WHERE (sources IS NULL OR sources='ofme')
              AND (
                LOWER(title) LIKE LOWER(?)
                OR LOWER(?) LIKE LOWER('%' || title || '%')
              )
            ORDER BY LENGTH(title) DESC
            LIMIT 1
            """,
            (f"%{title}%", title),
        ).fetchone()

    if match:
        # Link freetp URL to existing OFME game
        conn.execute(
            "UPDATE games SET freetp_url=?, sources='ofme,freetp' WHERE id=?",
            (freetp_url, match["id"]),
        )
        logger.debug("Linked freetp '%s' -> OFME id %d", title, match["id"])
    else:
        # Insert as freetp-only (ID >= 10_000_000)
        row = conn.execute(
            "SELECT COALESCE(MAX(id), 9999999) + 1 AS next_id FROM games WHERE id >= 10000000"
        ).fetchone()
        new_id = row["next_id"]

        conn.execute(
            """
            INSERT INTO games
                (id, title, category, slug, freetp_url, sources, scraped_at)
            VALUES (?, ?, 'freetp', ?, ?, 'freetp', ?)
            ON CONFLICT(id) DO NOTHING
            """,
            (new_id, title, g["slug"], freetp_url, now),
        )
        logger.debug("Inserted freetp-only '%s' as id %d", title, new_id)


def sync_freetp(max_pages: int = 0) -> int:
    """
    Scrape freetp.org and sync to DB.
    max_pages=0 means scrape all pages.
    Returns total number of game entries processed.
    """
    from database import get_connection, set_state

    total_pages = _detect_max_page()
    if not total_pages:
        raise RuntimeError("freetp: could not detect page count — site may be down")

    if max_pages:
        total_pages = min(total_pages, max_pages)

    logger.info("freetp: syncing %d pages", total_pages)
    processed = 0

    for page in range(1, total_pages + 1):
        logger.info("freetp page %d/%d", page, total_pages)
        games = scrape_freetp_page(page)

        conn = get_connection()
        for g in games:
            _upsert_freetp_game(conn, g)
            processed += 1
        conn.commit()
        conn.close()

        if page < total_pages:
            time.sleep(config.PAGE_DELAY + random.uniform(0, config.PAGE_JITTER))

    set_state("last_freetp_sync_at", datetime.now(timezone.utc).isoformat())
    logger.info("freetp sync complete. Processed %d game entries.", processed)
    return processed
