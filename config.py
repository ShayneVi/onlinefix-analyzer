import os
import random
from dataclasses import dataclass, field
from typing import Optional

DB_PATH = os.environ.get("OF_DB_PATH", os.path.join(os.path.dirname(__file__), "site", "games.db"))

PAGE_DELAY = float(os.environ.get("OF_PAGE_DELAY", "1.5"))
PAGE_JITTER = 0.5

STEAMDB_DELAY = float(os.environ.get("OF_STEAMDB_DELAY", "0.8"))
STEAMDB_JITTER = 0.5

MAX_RETRIES = 5

ONLINEFIX_BASE = "https://online-fix.me"
GAMES_PAGE = f"{ONLINEFIX_BASE}/games/"
GAMES_PAGE_URL = f"{ONLINEFIX_BASE}/games/page/{{page}}/"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]


def get_headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
    }


STEAM_STORE_SEARCH = "https://store.steampowered.com/search/"
STEAM_APP_DETAILS = "https://store.steampowered.com/api/appdetails"
STEAMSPY_API = "https://steamspy.com/api.php"


@dataclass
class ProxyConfig:
    enabled: bool = False
    host: str = "router.arpa"
    port: int = 9050
    credentials: list[tuple[str, str]] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "ProxyConfig":
        enabled = os.environ.get("OF_PROXY", "").lower() in ("1", "true", "yes")
        host = os.environ.get("OF_PROXY_HOST", "router.arpa")
        port = int(os.environ.get("OF_PROXY_PORT", "9050"))
        creds = []
        creds_env = os.environ.get("OF_PROXY_CREDENTIALS", "")
        if creds_env:
            for pair in creds_env.split(","):
                pair = pair.strip()
                if ":" in pair:
                    u, p = pair.split(":", 1)
                    creds.append((u, p))
        return cls(enabled=enabled, host=host, port=port, credentials=creds)

    def random_creds(self) -> Optional[tuple[str, str]]:
        if not self.credentials:
            return None
        return random.choice(self.credentials)

    @property
    def socks5_url(self) -> str:
        creds = self.random_creds()
        if creds:
            return f"socks5://{creds[0]}:{creds[1]}@{self.host}:{self.port}"
        return f"socks5://{self.host}:{self.port}"


PROXY = ProxyConfig.from_env()
