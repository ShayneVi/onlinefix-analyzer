import re
import time
import random
import logging
import sqlite3
import urllib.parse
from datetime import datetime, timezone
from typing import Optional

import httpx

import config

logger = logging.getLogger(__name__)


class RateLimitedError(Exception):
    pass


NOT_ON_STEAM = {
    "steam_appid": 0,
    "steam_name": "not on Steam",
    "review_score": 0,
    "review_count": 0,
    "review_desc": "",
    "price_usd": 0,
    "players_estimate": 0,
    "genres": "",
    "tags": "",
    "developer": "",
    "publisher": "",
    "metacritic_score": None,
    "is_multiplayer": False,
    "is_coop": False,
}


_session: Optional[httpx.Client] = None


def _get_session() -> httpx.Client:
    global _session
    if _session is not None:
        return _session

    headers = config.get_headers()
    transport = httpx.HTTPTransport(retries=3)
    kwargs = {
        "headers": headers,
        "timeout": httpx.Timeout(15.0, connect=5.0),
        "follow_redirects": True,
        "transport": transport,
    }
    if config.PROXY.enabled:
        kwargs["proxy"] = config.PROXY.socks5_url
    _session = httpx.Client(**kwargs)
    return _session


def _close_session():
    global _session
    if _session:
        _session.close()
        _session = None


def _search_steam_appid(game_title: str) -> Optional[int]:
    """Search Steam store. Returns appid or None. Raises RateLimitedError on persistent 429."""
    clean_title = re.sub(r"\s*\(.*?\)", "", game_title)
    clean_title = re.sub(r"\s*(онлайн|по сети|Online|Online Fix|Fix).*", "", clean_title, flags=re.I).strip()
    if not clean_title:
        return None

    params = {"term": clean_title, "l": "english"}
    url = f"{config.STEAM_STORE_SEARCH}?{urllib.parse.urlencode(params)}"
    client = _get_session()

    for attempt in range(1, 6):
        try:
            resp = client.get(url)
            if resp.status_code == 429:
                wait = 5 * (2 ** attempt)
                logger.warning("Steam search 429 for '%s', attempt %d/5, waiting %ds",
                               clean_title, attempt, wait)
                time.sleep(wait)
                continue
            if resp.status_code in (500, 502, 503, 504):
                logger.warning("Steam search 5xx for '%s', attempt %d/5", clean_title, attempt)
                time.sleep(2 ** attempt)
                continue
            if resp.status_code != 200:
                logger.debug("Search failed for '%s': %d", clean_title, resp.status_code)
                return None
            html = resp.text

            match = re.search(r'data-ds-appid="(\d+)"', html)
            if match:
                return int(match.group(1))

            matches = re.findall(r'/app/(\d+)/[^"]+', html)
            if matches:
                return int(matches[0])

            logger.debug("No appid found for '%s'", clean_title)
            return None
        except (httpx.RequestError, httpx.TimeoutException) as e:
            logger.debug("Search error for '%s' (attempt %d): %s", clean_title, attempt, e)
            if attempt < 3:
                time.sleep(2 ** attempt)
            continue

    raise RateLimitedError(f"Steam search 429 persisted for '{clean_title}'")


def get_store_details(appid: int) -> Optional[dict]:
    params = {"appids": appid}
    try:
        client = _get_session()
        resp = client.get(config.STEAM_APP_DETAILS, params=params)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning("Store API error for appid %d: %s", appid, e)
        return None

    if not data or str(appid) not in data:
        return None

    app_data = data[str(appid)]
    if not app_data.get("success"):
        return None

    details = app_data.get("data", {})
    result = {
        "steam_appid": appid,
        "steam_name": details.get("name", ""),
        "developer": ", ".join(details.get("developers", [])),
        "publisher": ", ".join(details.get("publishers", [])),
        "is_multiplayer": False,
        "is_coop": False,
        "genres": "",
        "review_score": 0,
        "review_count": 0,
        "review_desc": "",
        "price_usd": 0,
        "metacritic_score": None,
        "tags": "",
        "players_estimate": 0,
    }

    for cat in details.get("categories", []):
        desc = cat.get("description", "")
        if "Multi-player" in desc or "Online PvP" in desc:
            result["is_multiplayer"] = True
        if "Co-op" in desc:
            result["is_coop"] = True

    genres = details.get("genres", [])
    result["genres"] = ", ".join(g.get("description", "") for g in genres)

    price_overview = details.get("price_overview", {})
    if price_overview:
        result["price_usd"] = price_overview.get("final", 0) / 100.0

    if "metacritic" in details:
        result["metacritic_score"] = details["metacritic"].get("score")

    desc = details.get("detailed_description", "") + details.get("short_description", "")
    if re.search(r"\bmultiplayer\b", desc, re.I):
        result["is_multiplayer"] = True
    if re.search(r"\bco[- ]?op\b", desc, re.I):
        result["is_coop"] = True

    return result


def get_store_reviews(appid: int) -> dict:
    url = f"https://store.steampowered.com/appreviews/{appid}?json=1&language=all&purchase_type=all&num_per_page=0"
    try:
        client = _get_session()
        resp = client.get(url)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning("Reviews API error for %d: %s", appid, e)
        return {}

    query_summary = data.get("query_summary", {})
    return {
        "review_score": query_summary.get("total_positive", 0),
        "review_count": query_summary.get("total_reviews", 0),
        "review_desc": query_summary.get("review_score_desc", ""),
    }


def get_steamspy_data(appid: int) -> Optional[dict]:
    params = {"request": "appdetails", "appid": appid}
    try:
        client = _get_session()
        resp = client.get(config.STEAMSPY_API, params=params)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.debug("SteamSpy error for %d: %s", appid, e)
        return None

    if not data:
        return None

    result = {}
    for key in ("players_forever", "players_2weeks", "owners"):
        if key in data:
            val = data[key]
            if isinstance(val, str):
                val = val.replace(",", "")
                m = re.match(r"([\d.]+)\s*\.\.\s*([\d.]+)", val)
                if m:
                    val = (float(m.group(1)) + float(m.group(2))) / 2
                else:
                    try:
                        val = int(val)
                    except ValueError:
                        continue
            result["players_estimate"] = int(val)
            break

    tags = data.get("tags", {})
    if tags:
        top_tags = sorted(tags.items(), key=lambda x: x[1], reverse=True)[:10]
        result["tags"] = ", ".join(t[0] for t in top_tags)

        tag_names = {t.lower() for t in tags}
        result["is_multiplayer"] = any(
            t in tag_names for t in ("multiplayer", "pvp", "online pvp", "massively multiplayer")
        )
        result["is_coop"] = any(
            t in tag_names for t in ("co-op", "online co-op", "lan co-op", "local co-op")
        )

    return result


def lookup_game(game_id: int, game_title: str) -> Optional[dict]:
    appid = _search_steam_appid(game_title)
    if not appid:
        clean = re.sub(r" Online$", "", game_title, flags=re.I)
        clean = re.sub(r" по сети$", "", clean, flags=re.I)
        if clean != game_title:
            appid = _search_steam_appid(clean)
    if not appid:
        logger.debug("No Steam app found for '%s' (id=%d)", game_title, game_id)
        return None

    result = {
        "game_id": game_id,
        "steam_appid": appid,
        "steam_name": "",
        "review_score": 0,
        "review_count": 0,
        "review_desc": "",
        "price_usd": 0,
        "players_estimate": 0,
        "genres": "",
        "tags": "",
        "developer": "",
        "publisher": "",
        "metacritic_score": None,
        "is_multiplayer": False,
        "is_coop": False,
    }

    details = get_store_details(appid)
    if details:
        for k, v in details.items():
            if v is not None:
                result[k] = v

    reviews = get_store_reviews(appid)
    if reviews:
        result.update(reviews)

    spy = get_steamspy_data(appid)
    if spy:
        for k, v in spy.items():
            if v is not None:
                if k in ("is_multiplayer", "is_coop"):
                    result.setdefault(k, v)
                else:
                    result[k] = v

    logger.info(
        "Steam: %s (appid=%d) score=%d/%d players~%d",
        result["steam_name"] or game_title,
        appid,
        result["review_score"],
        result["review_count"],
        result["players_estimate"],
    )
    return result


def sync_steamdb(limit: int = 0, refresh: bool = False, purge: bool = False) -> int:
    """
    Fetch Steam data for games missing it. limit=0 means all.

    If refresh=True, also refetch games that already have Steam data.
    If purge=True, delete ALL steam data before fetching.
    """
    from database import (
        get_games_without_steam, upsert_steam_info, delete_steam_info,
        get_all_games, set_state, get_connection,
    )

    if purge:
        c = get_connection()
        c.execute("DELETE FROM steam_info")
        c.commit()
        c.close()
        logger.info("Purged all existing Steam data")

    db_conn = get_connection()

    if refresh:
        all_games = get_all_games(limit=99999)
        enriched = 0
        i = 0
        backoff = 10
        rate_limit_start = None
        while i < len(all_games):
            g = all_games[i]
            try:
                steam_data = lookup_game(g["id"], g["title"])
                rate_limit_start = None
            except RateLimitedError:
                if rate_limit_start is None:
                    rate_limit_start = time.time()
                elif time.time() - rate_limit_start > 300:
                    import sys
                    logger.error("Rate limit persisted for over 5 minutes. Failing gracefully.")
                    sys.exit(1)
                logger.warning("Rate limited! Pausing %ds...", backoff)
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
                _close_session()
                continue  # retry same game
            backoff = 10  # reset on success
            i += 1
            if steam_data:
                try:
                    upsert_steam_info(steam_data, conn=db_conn)
                    enriched += 1
                    logger.info("  [%d/%d] %s", enriched, len(all_games), g["title"][:60])
                except (sqlite3.IntegrityError, sqlite3.OperationalError) as e:
                    logger.warning("  Skipped '%s': %s", g["title"][:60], e)
            else:
                upsert_steam_info({**NOT_ON_STEAM, "game_id": g["id"]}, conn=db_conn)
            db_conn.commit()
            delay = config.STEAMDB_DELAY + random.uniform(0, config.STEAMDB_JITTER)
            time.sleep(delay)
            if limit and enriched >= limit:
                break
        db_conn.close()
        _close_session()
        set_state("last_steamdb_at", datetime.now(timezone.utc).isoformat())
        logger.info("SteamDB refresh complete. Enriched: %d", enriched)
        return enriched

    games = get_games_without_steam(limit=limit if limit else 99999)
    if not games:
        db_conn.close()
        _close_session()
        logger.info("All games already have Steam data")
        set_state("last_steamdb_at", datetime.now(timezone.utc).isoformat())
        return 0

    enriched = 0
    i = 0
    backoff = 10
    rate_limit_start = None
    while i < len(games):
        game = games[i]
        try:
            steam_data = lookup_game(game["id"], game["title"])
            rate_limit_start = None
        except RateLimitedError:
            if rate_limit_start is None:
                rate_limit_start = time.time()
            elif time.time() - rate_limit_start > 300:
                import sys
                logger.error("Rate limit persisted for over 5 minutes. Failing gracefully.")
                sys.exit(1)
            logger.warning("Rate limited! Pausing %ds...", backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
            _close_session()
            continue  # retry same game
        backoff = 10
        i += 1
        if steam_data:
            try:
                upsert_steam_info(steam_data, conn=db_conn)
                enriched += 1
            except (sqlite3.IntegrityError, sqlite3.OperationalError) as e:
                logger.warning("Skipped '%s': %s", game["title"][:60], e)
        else:
            upsert_steam_info({**NOT_ON_STEAM, "game_id": game["id"]}, conn=db_conn)
        db_conn.commit()
        delay = config.STEAMDB_DELAY + random.uniform(0, config.STEAMDB_JITTER)
        time.sleep(delay)

    db_conn.close()
    _close_session()
    set_state("last_steamdb_at", datetime.now(timezone.utc).isoformat())
    logger.info("SteamDB sync complete. Enriched %d/%d", enriched, len(games))
    return enriched
