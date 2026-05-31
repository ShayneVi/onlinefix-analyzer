#!/usr/bin/env python3
"""Online-Fix Analyzer - scrape, enrich, and analyze game fix data."""

import argparse
import logging
import sys
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from database import init_db, get_all_games, count_games, count_with_steam, get_state, get_state_int, get_connection
from scraper import sync
from steam_lookup import sync_steamdb
from freetp_scraper import sync_freetp
import config

logger = logging.getLogger("onlinefix")


def setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _time_ago(iso: str) -> str:
    if not iso:
        return "never"
    try:
        dt = datetime.fromisoformat(iso)
        now = datetime.now(timezone.utc)
        delta = now - dt
        if delta.days > 1:
            return f"{delta.days}d ago"
        if delta.days == 1:
            return "1d ago"
        hours = delta.seconds // 3600
        if hours > 1:
            return f"{hours}h ago"
        if hours == 1:
            return "1h ago"
        mins = delta.seconds // 60
        if mins > 1:
            return f"{mins}m ago"
        return "just now"
    except (ValueError, TypeError):
        return iso


def cmd_sync(args):
    init_db()
    try:
        total = sync()
        print(f"Sync complete. Upserted/updated: {total} games")
        print(f"Total in database: {count_games()}")
    except RuntimeError as e:
        print(f"ERROR: {e}")
        print("Sync stopped. Re-run to resume from this point.")
        sys.exit(1)


def cmd_freetp(args):
    init_db()
    try:
        total = sync_freetp(max_pages=args.max_pages)
        print(f"FreeTP sync complete. Processed: {total} game entries")
        print(f"Total in database: {count_games()}")
    except RuntimeError as e:
        print(f"ERROR: {e}")
        sys.exit(1)


def cmd_steamdb(args):
    init_db()
    enriched = sync_steamdb(limit=args.limit, refresh=args.refresh, purge=args.purge)
    print(f"Enriched {enriched} games. Total with Steam: {count_with_steam()}")


def cmd_status(args):
    init_db()
    total = count_games()
    with_steam = count_with_steam()

    last_page = get_state_int("last_page")
    total_pages = get_state_int("total_pages")
    scan_complete = get_state("scan_complete") == "1"
    last_sync = get_state("last_sync_at")
    last_steamdb = get_state("last_steamdb_at")

    print(f"  Games scraped:        {total}")
    print(f"  With Steam data:      {with_steam}")
    print(f"  Without Steam data:   {total - with_steam}")
    print()
    print(f"  Pages:                {last_page} / {total_pages} scanned")
    if scan_complete:
        print(f"  Scan state:           complete")
    else:
        print(f"  Scan state:           in progress (stopped at page {last_page})")
    print(f"  Last sync:            {_time_ago(last_sync) if last_sync else 'never'}")
    print(f"  Last steamdb:         {_time_ago(last_steamdb) if last_steamdb else 'never'}")
    print(f"  Database:             {config.DB_PATH}")
    print()

    # Image status
    img_dir = Path(__file__).parent / "site" / "img"
    if img_dir.exists():
        local = {f.stem for f in img_dir.glob("*.jpg")}
        conn = get_connection()
        rows = conn.execute("SELECT s.steam_appid, g.title, g.id FROM games g INNER JOIN steam_info s ON g.id = s.game_id WHERE s.steam_appid > 0").fetchall()
        conn.close()
        total_games = len(rows)
        with_img = sum(1 for r in rows if str(r["steam_appid"]) in local)
        missing = [r for r in rows if str(r["steam_appid"]) not in local]
        print(f"  Images on disk:       {len(local)}")
        print(f"  Games with image:    {with_img} / {total_games}")
        if missing:
            print(f"  Missing images:      {len(missing)}")
            print(f"  Missing game IDs:    {', '.join(str(r['id']) for r in missing[:10])}{'...' if len(missing) > 10 else ''}")
    else:
        print(f"  Images:              not built yet (run build_site.py)")


def cmd_export(args):
    init_db()
    games = get_all_games(limit=args.limit, offset=args.offset)
    if not games:
        print("No games found.")
        return

    if args.format == "csv":
        writer = csv.DictWriter(sys.stdout, fieldnames=games[0].keys())
        writer.writeheader()
        writer.writerows(games)
    elif args.format == "json":
        json.dump(games, sys.stdout, indent=2, ensure_ascii=False)
    elif args.format == "table":
        fmt = "{:<6}  {:<45}  {:<10}  {:>8}  {:>5}  {:>5}  {:>6}  {:>8}  {:>6}"
        print("\033[1m" + fmt.format(
            "ID", "Title", "Category", "Views", "Cmts", "Co-op", "Multi", "SteamID", "Rating"
        ) + "\033[0m")
        for g in games:
            review_str = ""
            if g.get("review_count") and g["review_count"] > 0:
                pct = int(g["review_score"] / g["review_count"] * 100)
                review_str = f"{pct}%"
            print(fmt.format(
                str(g["id"])[:6],
                str(g["title"])[:45],
                str(g.get("category", ""))[:10],
                str(g.get("views", 0))[:8],
                str(g.get("comments", 0))[:5],
                "Y" if g.get("has_coop") else "N",
                "Y" if g.get("has_multiplayer") else "N",
                str(g.get("steam_appid") or "")[:8],
                review_str[:6],
            ))


def cmd_search(args):
    init_db()
    from database import get_connection
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT g.*, s.steam_appid, s.steam_name, s.review_score, s.review_count,
               s.review_desc, s.price_usd, s.players_estimate, s.genres,
               s.tags, s.developer, s.publisher, s.metacritic_score,
               s.is_multiplayer as steam_multiplayer, s.is_coop as steam_coop,
               s.fetched_at as steam_fetched_at
        FROM games g
        LEFT JOIN steam_info s ON g.id = s.game_id
        WHERE g.title LIKE ?
        ORDER BY g.views DESC
        """,
        (f"%{args.name}%",),
    ).fetchall()
    conn.close()

    if not rows:
        print(f"No games found matching '{args.name}'")
        return

    print(f"\nFound {len(rows)} game(s) matching '{args.name}':\n")
    for r in rows:
        g = dict(r)
        print(f"  {'─' * 60}")
        print(f"  Title:        {g['title']}")
        print(f"  Category:     {g['category']}")
        print(f"  URL:          {g['url']}")
        print(f"  Views:        {g['views']:,}")
        print(f"  Comments:     {g['comments']}")
        print(f"  Release date: {g['release_date'] or 'N/A'}")
        print(f"  Fix platform: {g['fix_platform'] or 'N/A'}")
        print(f"  Co-op:        {'Yes' if g['has_coop'] else 'No'}")
        print(f"  Multiplayer:  {'Yes' if g['has_multiplayer'] else 'No'}")
        if g.get('last_updated') and len(g['last_updated']) > 3:
            print(f"  Last updated: {g['last_updated']}")
        print()
        print(f"  --- Steam ---")
        if g.get('steam_appid'):
            pct = 0
            if g.get('review_count') and g['review_count'] > 0:
                pct = int(g['review_score'] / g['review_count'] * 100)
            print(f"  Steam name:   {g.get('steam_name') or g['title']}")
            print(f"  AppID:        {g['steam_appid']}")
            print(f"  Reviews:      {pct}% positive ({g['review_count']:,} total)")
            if g.get('review_desc'):
                print(f"  Review desc:  {g['review_desc']}")
            if g.get('price_usd'):
                print(f"  Price:        ${g['price_usd']}")
            if g.get('players_estimate'):
                print(f"  Players:      ~{g['players_estimate']:,}")
            if g.get('genres'):
                print(f"  Genres:       {g['genres']}")
            if g.get('tags'):
                print(f"  Tags:         {g['tags']}")
            if g.get('developer'):
                print(f"  Developer:    {g['developer']}")
            if g.get('publisher'):
                print(f"  Publisher:    {g['publisher']}")
            if g.get('metacritic_score'):
                print(f"  Metacritic:   {g['metacritic_score']}")
        else:
            print(f"  No Steam data. Run 'steamdb' to fetch.")
        print()



def cmd_top(args):
    init_db()
    from database import get_connection
    conn = get_connection()
    order_map = {
        "views": "g.views",
        "comments": "g.comments",
        "rating": "s.review_score",
        "reviews": "s.review_count",
    }
    by = args.by
    if by not in order_map:
        print(f"Invalid sort: {by}. Use: {', '.join(order_map.keys())}")
        return
    rows = conn.execute(
        f"""
        SELECT g.id, g.title, g.views, g.comments, g.has_coop, g.has_multiplayer,
               s.review_score, s.review_count, s.review_desc, s.steam_appid,
               s.price_usd, s.players_estimate
        FROM games g
        LEFT JOIN steam_info s ON g.id = s.game_id
        ORDER BY {order_map[by]} DESC
        LIMIT ?
        """,
        (args.limit,),
    ).fetchall()
    conn.close()

    print(f"\nTop {args.limit} games by {by}:\n")
    print(f"{'#':<4} {'Title':<50} {'Views':>8} {'Cmts':>5} {'Co-op':>5} {'Multi':>6} {'Rating':>12} {'Price':>6}")
    print("-" * 100)
    for i, r in enumerate(rows, 1):
        review_str = "-"
        if r["review_score"] is not None and r["review_count"] and r["review_count"] > 0:
            pct = int(r["review_score"] / r["review_count"] * 100)
            review_str = f"{pct}% ({r['review_count']})"
        price = f"${r['price_usd']}" if r['price_usd'] else "-"
        print(f"{i:<4} {r['title'][:50]:<50} {r['views']:>8} {r['comments']:>5} {'Y' if r['has_coop'] else 'N':>5} {'Y' if r['has_multiplayer'] else 'N':>6} {review_str:>12} {price:>6}")


def main():
    parser = argparse.ArgumentParser(
        description="Online-Fix Analyzer - scrape and analyze game fix data"
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose debug output")
    parser.add_argument("--proxy", action="store_true", help="Enable SOCKS5 proxy for SteamDB calls")
    parser.add_argument("--proxy-host", default="router.arpa", help="Proxy host")
    parser.add_argument("--proxy-port", type=int, default=9050, help="Proxy port")
    parser.add_argument("--proxy-creds", default="",
                        help="Proxy credentials as user1:pass1,user2:pass2,...")

    sub = parser.add_subparsers(dest="command", help="Commands")

    sub.add_parser("sync", help="Sync games from online-fix.me (state-aware, resumable)")

    p_freetp = sub.add_parser("freetp", help="Sync game fix links from freetp.org")
    p_freetp.add_argument("-n", "--max-pages", type=int, default=0,
                          help="Max pages to scrape (0=all)")

    p_steamdb = sub.add_parser("steamdb", help="Fetch Steam/SteamSpy data for scraped games")
    p_steamdb.add_argument("-n", "--limit", type=int, default=0,
                           help="Max games to enrich (0=all)")
    p_steamdb.add_argument("--refresh", action="store_true",
                           help="Re-fetch Steam data for all games")
    p_steamdb.add_argument("--purge", action="store_true",
                           help="Delete all existing Steam data before fetching")

    sub.add_parser("status", help="Show database stats and sync state")

    p_search = sub.add_parser("search", help="Search games by name")
    p_search.add_argument("name", help="Game name to search (LIKE query)")

    p_export = sub.add_parser("export", help="Export games to stdout")
    p_export.add_argument("-f", "--format", choices=["csv", "json", "table"],
                          default="table")
    p_export.add_argument("-n", "--limit", type=int, default=100)
    p_export.add_argument("--offset", type=int, default=0)

    p_top = sub.add_parser("top", help="Show top games")
    p_top.add_argument("-n", "--limit", type=int, default=20)
    p_top.add_argument("-b", "--by", choices=["views", "comments", "rating", "reviews"],
                       default="views")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    setup_logging(args.verbose)

    if args.proxy:
        creds = []
        if args.proxy_creds:
            for pair in args.proxy_creds.split(","):
                pair = pair.strip()
                if ":" in pair:
                    u, p = pair.split(":", 1)
                    creds.append((u, p))
        config.PROXY = config.ProxyConfig(
            enabled=True,
            host=args.proxy_host,
            port=args.proxy_port,
            credentials=creds,
        )
        logger.info("Proxy enabled: %s:%d (%d credentials)",
                     args.proxy_host, args.proxy_port, len(creds))

    cmd_map = {
        "sync": cmd_sync,
        "freetp": cmd_freetp,
        "steamdb": cmd_steamdb,
        "status": cmd_status,
        "search": cmd_search,
        "export": cmd_export,
        "top": cmd_top,
    }
    cmd_map[args.command](args)


if __name__ == "__main__":
    main()
