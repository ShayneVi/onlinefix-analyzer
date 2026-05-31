import re
import random
import time
import logging
from datetime import datetime, timezone
from typing import Optional

try:
    from curl_cffi import requests as curlreqs
    HAS_CURL_CFFI = True
except ImportError:
    import httpx
    HAS_CURL_CFFI = False

from bs4 import BeautifulSoup

import config

logger = logging.getLogger(__name__)

CHALLENGE_MARKERS = ["window.K3", "cf-challenge", "Just a moment",
                     "Checking your browser", "DDoS protection"]


def _fetch(url: str, retries: int = config.MAX_RETRIES) -> str:
    """Fetch a page. Raises RuntimeError if all retries exhausted."""
    if not HAS_CURL_CFFI:
        logger.warning("curl_cffi not available, falling back to httpx")
        return _fetch_httpx(url, retries)

    impersonates = ["chrome124", "chrome123", "chrome120", "firefox126", "edge101"]
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            headers = config.get_headers()
            resp = curlreqs.get(
                url,
                headers=headers,
                impersonate=impersonates[attempt % len(impersonates)],
                timeout=30,
            )
            if resp.status_code in (429, 403, 503):
                wait = 5 * (2 ** attempt)
                logger.warning("Got %d on attempt %d/%d, waiting %ds",
                               resp.status_code, attempt, retries, wait)
                time.sleep(wait)
                continue

            if resp.status_code != 200:
                logger.warning("Status %d on attempt %d/%d",
                               resp.status_code, attempt, retries)
                time.sleep(2 ** attempt)
                continue

            html = resp.text
            head = html[:2000].lower()
            blocked = any(m.lower() in head for m in CHALLENGE_MARKERS)
            if blocked or len(html) < 30000:
                wait = 5 * (2 ** attempt)
                logger.warning("Challenge/truncated page (len=%d, attempt %d/%d), waiting %ds",
                               len(html), attempt, retries, wait)
                time.sleep(wait)
                continue

            return html
        except Exception as e:
            last_error = e
            logger.warning("Request failed (attempt %d/%d): %s", attempt, retries, e)
            if attempt < retries:
                time.sleep(2 ** attempt)

    raise RuntimeError(f"Failed to fetch {url} after {retries} attempts: {last_error}")


def _fetch_httpx(url: str, retries: int = 3) -> str:
    import httpx
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            with httpx.Client(headers=config.get_headers(), timeout=30,
                              follow_redirects=True) as client:
                resp = client.get(url)
                resp.raise_for_status()
                return resp.text
        except Exception as e:
            last_error = e
            logger.warning("httpx request failed (attempt %d/%d): %s", attempt, retries, e)
            if attempt < retries:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed to fetch {url} after {retries} attempts: {last_error}")


def parse_game_article(article: BeautifulSoup, base_url: str) -> Optional[dict]:
    try:
        big_link = article.select_one("a.big-link")
        if not big_link:
            return None
        url = big_link.get("href", "")
        if url and not url.startswith("http"):
            from urllib.parse import urljoin as uj
            url = uj(base_url, url)

        match = re.match(r".*/games/([^/]+)/(\d+)-(.+)\.html$", url)
        if not match:
            return None
        category = match.group(1)
        game_id = int(match.group(2))
        slug = match.group(3)

        title_el = article.select_one("h2.title")
        title = title_el.text.strip() if title_el else ""

        info_date = article.select_one("span.info-date")
        views = 0
        comments = 0
        posted_at = ""
        if info_date:
            time_el = info_date.select_one("time")
            if time_el:
                posted_at = time_el.get("datetime", "")
            eye_icon = info_date.select_one("i.fa-eye")
            if eye_icon and eye_icon.next_sibling:
                m = re.search(r"(\d[\d\s]*)", str(eye_icon.next_sibling))
                if m:
                    views = int(m.group(1).replace(" ", ""))
            comment_link = info_date.select_one("a[href*='#comment']")
            if comment_link:
                comment_text = comment_link.text.strip()
                if comment_text.isdigit():
                    comments = int(comment_text)

        preview = article.select_one("div.preview-text")
        release_date = ""
        fix_platform = ""
        has_coop = False
        has_multiplayer = False

        if preview:
            text = preview.get_text("\n", strip=True)
            release_match = re.search(
                r"(?:Game\s*[Rr]elease|[Рр]елиз\s*игры|Выход\s*игры)[:\s]*(.*?)(?:\n|$)",
                text
            )
            if release_match:
                release_date = release_match.group(1).strip()

            plat_match = re.search(
                r"(?:Play\s*via|[Ии]гра\s*через|Тип\s*фикса)[:\s]*(.*?)(?:\n|$)",
                text
            )
            if plat_match:
                fix_platform = plat_match.group(1).strip()

            coop_icons = preview.select("span.fa-check, span.fa-times")
            if len(coop_icons) >= 1:
                has_coop = "fa-check" in coop_icons[0].get("class", [])
            if len(coop_icons) >= 2:
                has_multiplayer = "fa-check" in coop_icons[1].get("class", [])

        edit_div = article.select_one("div.edit")
        last_updated = ""
        if edit_div:
            tu = edit_div.text.strip().replace("\xa0", " ")
            if tu and len(tu) > 5:
                last_updated = tu

        poster_url = ""
        img = article.select_one("img.lazyload")
        if img:
            poster_url = img.get("data-src", img.get("src", ""))
            if poster_url and not poster_url.startswith("http"):
                from urllib.parse import urljoin as uj
                poster_url = uj(base_url, poster_url)

        return {
            "id": game_id,
            "title": title,
            "category": category,
            "slug": slug,
            "posted_at": posted_at,
            "views": views,
            "comments": comments,
            "release_date": release_date,
            "fix_platform": fix_platform,
            "has_coop": has_coop,
            "has_multiplayer": has_multiplayer,
            "last_updated": last_updated,
            "url": url,
            "poster_url": poster_url,
        }
    except Exception as e:
        logger.debug("Failed to parse article: %s", e)
        return None


def _scrape_page(page_num: int) -> tuple[list[dict], list[int]]:
    """Fetch a single page. Returns (parsed games, list of game IDs)."""
    if page_num == 1:
        url = config.GAMES_PAGE
    else:
        url = config.GAMES_PAGE_URL.format(page=page_num)
    logger.info("Page %d: %s", page_num, url)

    html = _fetch(url)
    soup = BeautifulSoup(html, "lxml")
    articles = soup.select("article.news")
    games = []
    ids = []
    for article in articles:
        game = parse_game_article(article, config.ONLINEFIX_BASE)
        if game:
            games.append(game)
            ids.append(game["id"])
    logger.info("Page %d: %d games", page_num, len(games))
    return games, ids


def _detect_total_pages() -> int:
    html = _fetch(config.GAMES_PAGE)
    soup = BeautifulSoup(html, "lxml")
    nav = soup.select_one("nav.pagination, div.navigation, div.page-navigation, div.pages, div.dle-pages")
    if nav:
        links = nav.select("a")
        nums = []
        for link in links:
            try:
                nums.append(int(link.text.strip()))
            except ValueError:
                m = re.search(r"/page/(\d+)", link.get("href", ""))
                if m:
                    nums.append(int(m.group(1)))
        if nums:
            total = max(nums)
            logger.info("Detected %d total pages", total)
            return total

    all_links = soup.select('a[href*="/page/"]')
    nums = []
    for link in all_links:
        m = re.search(r"/page/(\d+)", link.get("href", ""))
        if m:
            nums.append(int(m.group(1)))
    if nums:
        total = max(nums)
        logger.info("Detected %d total pages from links", total)
        return total
    return 1


def _page_is_known(page_num: int) -> bool:
    """Check if all games on this page and page+1 are already in DB and up to date."""
    if page_num == 1:
        url = config.GAMES_PAGE
    else:
        url = config.GAMES_PAGE_URL.format(page=page_num)

    html = _fetch(url)
    soup = BeautifulSoup(html, "lxml")
    articles = soup.select("article.news")
    games = []
    ids = []
    for article in articles:
        game = parse_game_article(article, config.ONLINEFIX_BASE)
        if game:
            games.append(game)
            ids.append(game["id"])
    if not ids:
        return False

    from database import get_games_last_updated
    db_data = get_games_last_updated(ids)
    if len(db_data) != len(ids):
        return False
        
    for game in games:
        if db_data.get(game["id"]) != game.get("last_updated"):
            return False

    # Also check page+1
    next_url = config.GAMES_PAGE_URL.format(page=page_num + 1)
    try:
        html2 = _fetch(next_url)
        soup2 = BeautifulSoup(html2, "lxml")
        articles2 = soup2.select("article.news")
        games2 = []
        ids2 = []
        for article in articles2:
            game = parse_game_article(article, config.ONLINEFIX_BASE)
            if game:
                games2.append(game)
                ids2.append(game["id"])
        if ids2:
            db_data2 = get_games_last_updated(ids2)
            if len(db_data2) != len(ids2):
                return False
            for game in games2:
                if db_data2.get(game["id"]) != game.get("last_updated"):
                    return False
            return True
        return True
    except RuntimeError:
        # If page+1 fails, assume it's a dead page (end of content)
        return True


def _upsert_games(games: list[dict]):
    from database import upsert_games_bulk
    upsert_games_bulk(games)


def sync() -> int:
    """
    State-aware sync with online-fix.me.

    First run: scan all pages from 1 to total_pages.
    Re-run with scan_complete: quick catch-up from page 1 until stale.
    Re-run with interrupted scan: resume from last_page-1.
    On any fetch failure: raise RuntimeError (no page skipping).
    """
    from database import get_state, get_state_int, set_state

    total_pages = _detect_total_pages()
    set_state("total_pages", str(total_pages))

    last_page = get_state_int("last_page")
    scan_complete = get_state("scan_complete") == "1"

    logger.info("State: total_pages=%d, last_page=%d, scan_complete=%s",
                total_pages, last_page, scan_complete)

    total_upserted = 0

    if scan_complete:
        logger.info("Quick catch-up: scanning from page 1 until stale")
        for page in range(1, total_pages + 1):
            if page > 1 and _page_is_known(page):
                logger.info("Page %d and page %d fully known, caught up", page, page + 1)
                break
            games, ids = _scrape_page(page)
            _upsert_games(games)
            total_upserted += len(games)
            set_state("last_page", str(page))
            if page < total_pages:
                time.sleep(config.PAGE_DELAY + random.uniform(0, config.PAGE_JITTER))
    else:
        # Resume interrupted scan or first run
        resume_from = max(last_page - 1, 1)
        logger.info("Resuming full scan from page %d", resume_from)

        for page in range(resume_from, total_pages + 1):
            games, ids = _scrape_page(page)
            if not games and page > 2:
                logger.info("No games on page %d, reached end of content", page)
                break
            _upsert_games(games)
            total_upserted += len(games)
            set_state("last_page", str(page))
            if page < total_pages:
                time.sleep(config.PAGE_DELAY + random.uniform(0, config.PAGE_JITTER))

        # Full scan done. Now quick catch-up for games added during scan.
        if not scan_complete:
            logger.info("Full scan done, running quick catch-up")
            for page in range(1, total_pages + 1):
                if page > 1 and _page_is_known(page):
                    logger.info("Page %d and %d fully known, caught up", page, page + 1)
                    break
                games, ids = _scrape_page(page)
                _upsert_games(games)
                total_upserted += len(games)
                if page < total_pages:
                    time.sleep(config.PAGE_DELAY + random.uniform(0, config.PAGE_JITTER))

    set_state("scan_complete", "1")
    set_state("last_sync_at", datetime.now(timezone.utc).isoformat())

    logger.info("Sync complete. Total upserted: %d", total_upserted)
    return total_upserted
