# onlinefix-analyzer

Scrapes [online-fix.me](https://online-fix.me) for game fixes and enriches them with Steam data (ratings, player counts, genres, prices). Generates a static filterable web page — automatically updated daily via GitHub Actions.

### Features

- 1800+ games scraped from 63 pages
- Steam ratings, review counts, player estimates (Store API + SteamSpy)
- Co-op / Multiplayer detection from the fix metadata
- Genre multi-select filter + sort by views, rating, players, release date
- Preview images from Steam CDN (all local, no hotlinking)
- Linux launch guide with Wine/Proton instructions
- Resumable scraping — picks up where it left off
- All games enriched — no redundant API calls on re-run

### Commands

| Command | Purpose |
|---|---|
| `python main.py sync` | Scrape games from online-fix.me (state-aware, resumable) |
| `python main.py steamdb` | Fetch Steam/SteamSpy data for games missing it |
| `python main.py status` | Show database stats and image coverage |
| `python main.py search "name"` | Search games by title |
| `python main.py top -b rating` | Show top games by views / rating / comments |
| `python main.py export -f json` | Export as CSV or JSON |
| `python build_site.py` | Generate static `site/index.html` |

### Deploy

The included GitHub Action syncs daily at 6am UTC: scrape → enrich → build → deploy to GitHub Pages.

1. Push this repo to GitHub
2. Repo → Settings → Pages → Source: **GitHub Actions**
3. Manually trigger the workflow in Actions tab, or wait for the daily cron
4. Site will be at `https://<user>.github.io/onlinefix-analyzer/`

### Data sources

- Game list: [online-fix.me](https://online-fix.me)
- Ratings & player counts: Steam Store API + [SteamSpy](https://steamspy.com)
- Preview images: Steam CDN (Akamai / Fastly)
- Linux guide: generic Wine/Proton configuration

### License

MIT
