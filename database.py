import sqlite3
from datetime import datetime, timezone
from typing import Optional

import config

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT,
    slug TEXT,
    posted_at TEXT,
    views INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    release_date TEXT,
    fix_platform TEXT,
    has_coop INTEGER DEFAULT 0,
    has_multiplayer INTEGER DEFAULT 0,
    last_updated TEXT,
    url TEXT UNIQUE,
    poster_url TEXT,
    scraped_at TEXT,
    freetp_url TEXT,
    sources TEXT DEFAULT 'ofme'
);

CREATE TABLE IF NOT EXISTS steam_info (
    game_id INTEGER PRIMARY KEY REFERENCES games(id),
    steam_appid INTEGER,
    steam_name TEXT,
    review_score INTEGER,
    review_count INTEGER,
    review_desc TEXT,
    price_usd REAL,
    players_estimate INTEGER,
    genres TEXT,
    tags TEXT,
    developer TEXT,
    publisher TEXT,
    metacritic_score INTEGER,
    is_multiplayer INTEGER DEFAULT 0,
    is_coop INTEGER DEFAULT 0,
    fetched_at TEXT
);

CREATE TABLE IF NOT EXISTS scraper_state (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE INDEX IF NOT EXISTS idx_games_category ON games(category);
CREATE INDEX IF NOT EXISTS idx_games_comments ON games(comments);
CREATE INDEX IF NOT EXISTS idx_games_views ON games(views);
CREATE INDEX IF NOT EXISTS idx_steam_appid ON steam_info(steam_appid);
CREATE INDEX IF NOT EXISTS idx_steam_review_score ON steam_info(review_score);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH, timeout=10)
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.executescript(SCHEMA_SQL)
    # Migration: remove UNIQUE constraint on steam_appid from existing DBs
    cur = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='steam_info'")
    schema = (cur.fetchone() or ["", ""])[0] or ""
    if "steam_appid INTEGER UNIQUE" in schema or "unique" in schema.lower() and "steam_appid" in schema.lower():
        conn.executescript("""
            BEGIN TRANSACTION;
            CREATE TABLE IF NOT EXISTS steam_info_new (
                game_id INTEGER PRIMARY KEY REFERENCES games(id),
                steam_appid INTEGER,
                steam_name TEXT,
                review_score INTEGER,
                review_count INTEGER,
                review_desc TEXT,
                price_usd REAL,
                players_estimate INTEGER,
                genres TEXT,
                tags TEXT,
                developer TEXT,
                publisher TEXT,
                metacritic_score INTEGER,
                is_multiplayer INTEGER DEFAULT 0,
                is_coop INTEGER DEFAULT 0,
                fetched_at TEXT
            );
            INSERT OR IGNORE INTO steam_info_new SELECT * FROM steam_info;
            DROP TABLE steam_info;
            ALTER TABLE steam_info_new RENAME TO steam_info;
            CREATE INDEX IF NOT EXISTS idx_steam_appid ON steam_info(steam_appid);
            CREATE INDEX IF NOT EXISTS idx_steam_review_score ON steam_info(review_score);
            COMMIT;
        """)
    # Migration: add freetp_url and sources columns if they don't exist
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(games)").fetchall()}
    if "freetp_url" not in existing_cols:
        conn.execute("ALTER TABLE games ADD COLUMN freetp_url TEXT")
    if "sources" not in existing_cols:
        conn.execute("ALTER TABLE games ADD COLUMN sources TEXT DEFAULT 'ofme'")
        # Back-fill existing rows so they're correctly labelled
        conn.execute("UPDATE games SET sources='ofme' WHERE sources IS NULL")

    conn.commit()
    conn.close()


def upsert_game(game: dict, conn: sqlite3.Connection | None = None):
    close = conn is None
    if conn is None:
        conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO games (id, title, category, slug, posted_at, views, comments,
                           release_date, fix_platform, has_coop, has_multiplayer,
                           last_updated, url, poster_url, scraped_at)
        VALUES (:id, :title, :category, :slug, :posted_at, :views, :comments,
                :release_date, :fix_platform, :has_coop, :has_multiplayer,
                :last_updated, :url, :poster_url, :scraped_at)
        ON CONFLICT(id) DO UPDATE SET
            title=excluded.title,
            category=excluded.category,
            views=excluded.views,
            comments=excluded.comments,
            posted_at=excluded.posted_at,
            release_date=excluded.release_date,
            fix_platform=excluded.fix_platform,
            has_coop=excluded.has_coop,
            has_multiplayer=excluded.has_multiplayer,
            last_updated=excluded.last_updated,
            poster_url=excluded.poster_url,
            scraped_at=excluded.scraped_at
        """,
        {**game, "scraped_at": now},
    )
    if close:
        conn.commit()
        conn.close()

def upsert_games_bulk(games: list[dict]):
    if not games:
        return
    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()
    for g in games:
        g["scraped_at"] = now
    
    conn.executemany(
        """
        INSERT INTO games (id, title, category, slug, posted_at, views, comments,
                           release_date, fix_platform, has_coop, has_multiplayer,
                           last_updated, url, poster_url, scraped_at)
        VALUES (:id, :title, :category, :slug, :posted_at, :views, :comments,
                :release_date, :fix_platform, :has_coop, :has_multiplayer,
                :last_updated, :url, :poster_url, :scraped_at)
        ON CONFLICT(id) DO UPDATE SET
            title=excluded.title,
            category=excluded.category,
            views=excluded.views,
            comments=excluded.comments,
            posted_at=excluded.posted_at,
            release_date=excluded.release_date,
            fix_platform=excluded.fix_platform,
            has_coop=excluded.has_coop,
            has_multiplayer=excluded.has_multiplayer,
            last_updated=excluded.last_updated,
            poster_url=excluded.poster_url,
            scraped_at=excluded.scraped_at
        """,
        games,
    )
    conn.commit()
    conn.close()


def upsert_steam_info(data: dict, conn: sqlite3.Connection | None = None):
    close = conn is None
    if conn is None:
        conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO steam_info (game_id, steam_appid, steam_name, review_score,
                                review_count, review_desc, price_usd, players_estimate,
                                genres, tags, developer, publisher, metacritic_score,
                                is_multiplayer, is_coop, fetched_at)
        VALUES (:game_id, :steam_appid, :steam_name, :review_score,
                :review_count, :review_desc, :price_usd, :players_estimate,
                :genres, :tags, :developer, :publisher, :metacritic_score,
                :is_multiplayer, :is_coop, :fetched_at)
        ON CONFLICT(game_id) DO UPDATE SET
            steam_appid=excluded.steam_appid,
            steam_name=excluded.steam_name,
            review_score=excluded.review_score,
            review_count=excluded.review_count,
            review_desc=excluded.review_desc,
            price_usd=excluded.price_usd,
            players_estimate=excluded.players_estimate,
            genres=excluded.genres,
            tags=excluded.tags,
            developer=excluded.developer,
            publisher=excluded.publisher,
            metacritic_score=excluded.metacritic_score,
            is_multiplayer=excluded.is_multiplayer,
            is_coop=excluded.is_coop,
            fetched_at=excluded.fetched_at
        """,
        {**data, "fetched_at": now},
    )
    if close:
        conn.commit()
        conn.close()


def get_state(key: str) -> Optional[str]:
    conn = get_connection()
    row = conn.execute("SELECT value FROM scraper_state WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else None


def get_state_int(key: str) -> int:
    val = get_state(key)
    if val is None:
        return 0
    try:
        return int(val)
    except ValueError:
        return 0


def set_state(key: str, value: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO scraper_state(key, value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    conn.commit()
    conn.close()


def count_known_ids(ids: list[int]) -> int:
    """Return how many of the given game IDs already exist in the DB."""
    if not ids:
        return 0
    conn = get_connection()
    placeholders = ",".join("?" * len(ids))
    row = conn.execute(
        f"SELECT COUNT(*) as cnt FROM games WHERE id IN ({placeholders})",
        ids,
    ).fetchone()
    conn.close()
    return row["cnt"]


def get_games_last_updated(ids: list[int]) -> dict[int, str]:
    if not ids:
        return {}
    conn = get_connection()
    placeholders = ",".join("?" * len(ids))
    rows = conn.execute(
        f"SELECT id, last_updated FROM games WHERE id IN ({placeholders})",
        ids,
    ).fetchall()
    conn.close()
    return {r["id"]: r["last_updated"] for r in rows}


def get_games_without_steam(limit: int = 50) -> list:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT g.* FROM games g
        LEFT JOIN steam_info s ON g.id = s.game_id
        WHERE s.game_id IS NULL
        ORDER BY g.views DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_steam_info(game_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM steam_info WHERE game_id=?", (game_id,))
    conn.commit()
    conn.close()


def get_all_games(limit: int = 100, offset: int = 0) -> list:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT g.*, s.steam_appid, s.review_score, s.review_count, s.review_desc,
               s.price_usd, s.players_estimate, s.genres, s.metacritic_score,
               s.is_multiplayer as steam_multiplayer, s.is_coop as steam_coop
        FROM games g
        LEFT JOIN steam_info s ON g.id = s.game_id
        ORDER BY g.posted_at DESC
        LIMIT ? OFFSET ?
        """,
        (limit, offset),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_games() -> int:
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) as cnt FROM games").fetchone()
    conn.close()
    return row["cnt"]


def count_with_steam() -> int:
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) as cnt FROM steam_info").fetchone()
    conn.close()
    return row["cnt"]
