import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://v3.football.api-sports.io"

# Free plan allows 10 req/min — sleep between calls to stay under it.
RATE_LIMIT_SLEEP_SECONDS = 1

# Brasileirão Série A, Copa do Brasil
ALLOWED_LEAGUE_IDS = {71, 73}

# Temporada padrão de todas as consultas; configurável por FOOTBALL_SEASON.
_DEFAULT_SEASON = settings.FOOTBALL_SEASON

STATUS_MAP = {
    "NS": "scheduled",
    "1H": "live",
    "HT": "live",
    "2H": "live",
    "ET": "live",
    "BT": "live",
    "P": "live",
    "SUSP": "live",
    "INT": "live",
    "LIVE": "live",
    "FT": "finished",
    "AET": "finished",
    "PEN": "finished",
    "PST": "postponed",
    "CANC": "postponed",
    "ABD": "postponed",
    "AWD": "postponed",
    "WO": "postponed",
}


def _map_status(short: Optional[str]) -> str:
    return STATUS_MAP.get(short or "", "scheduled")


def _get(path: str, params: dict) -> Optional[dict]:
    """Rate-limited GET against API-Football.

    Returns the parsed JSON body, or None if the request failed at the
    transport level, returned a non-200 status, or the API itself reported
    an error (e.g. a plan restriction) — callers should fall back to
    mocked data in that case.
    """
    time.sleep(RATE_LIMIT_SLEEP_SECONDS)

    try:
        response = httpx.get(
            f"{BASE_URL}{path}",
            headers={"x-apisports-key": settings.FOOTBALL_API_KEY},
            params=params,
            timeout=10,
        )
    except httpx.HTTPError as exc:
        logger.error("API-Football request failed: %s %s -> %s", path, params, exc)
        return None

    if response.status_code != 200:
        logger.error(
            "API-Football returned status %s for %s %s: %s",
            response.status_code,
            path,
            params,
            response.text[:500],
        )
        return None

    data = response.json()
    errors = data.get("errors")
    if errors:
        logger.error("API-Football returned errors for %s %s: %s", path, params, errors)
        return None

    return data


# ---------------------------------------------------------------------------
# Mocked fallbacks — used when the external API is unreachable or errors out.
# ---------------------------------------------------------------------------

def _mock_competitions() -> list[dict]:
    return [
        {
            "external_api_id": "comp_brasileirao_2026",
            "name": "Brasileirão 2026",
            "season": "2026",
            "type": "league",
        }
    ]


def _mock_games() -> list[dict]:
    now = datetime.now(timezone.utc)
    return [
        {
            "external_api_id": "game_fla_pal_r1",
            "home_team": {
                "external_api_id": "team_fla",
                "name": "Flamengo",
                "crest_url": None,
            },
            "away_team": {
                "external_api_id": "team_pal",
                "name": "Palmeiras",
                "crest_url": None,
            },
            "kickoff_at": now + timedelta(hours=2),
            "status": "scheduled",
            "home_score": None,
            "away_score": None,
            "locks_at": now + timedelta(hours=2) - timedelta(minutes=30),
            "round_name": "Rodada 1",
        },
        {
            "external_api_id": "game_cor_sao_r1",
            "home_team": {
                "external_api_id": "team_cor",
                "name": "Corinthians",
                "crest_url": None,
            },
            "away_team": {
                "external_api_id": "team_sao",
                "name": "São Paulo",
                "crest_url": None,
            },
            "kickoff_at": now + timedelta(hours=4),
            "status": "scheduled",
            "home_score": None,
            "away_score": None,
            "locks_at": now + timedelta(hours=4) - timedelta(minutes=30),
            "round_name": "Rodada 1",
        },
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_competitions(season: int = _DEFAULT_SEASON) -> list[dict]:
    data = _get("/leagues", {"country": "Brazil", "season": season})
    if data is None:
        return _mock_competitions()

    competitions = []
    for entry in data.get("response", []):
        league = entry.get("league", {})
        league_id = league.get("id")
        if league_id not in ALLOWED_LEAGUE_IDS:
            continue
        competitions.append(
            {
                "external_api_id": str(league_id),
                "name": league.get("name"),
                "season": str(season),
                "type": (league.get("type") or "League").lower(),
            }
        )

    return competitions or _mock_competitions()


def fetch_rounds(league_id: int | str, season: int = _DEFAULT_SEASON) -> list[str]:
    data = _get("/fixtures/rounds", {"league": league_id, "season": season})
    if data is None:
        return []
    return data.get("response", [])


def fetch_current_round(league_id: int | str, season: int = _DEFAULT_SEASON) -> Optional[str]:
    data = _get(
        "/fixtures/rounds",
        {"league": league_id, "season": season, "current": "true"},
    )
    if data is None:
        return None
    rounds = data.get("response", [])
    return rounds[0] if rounds else None


def fetch_games(
    league_id: int | str,
    season: int = _DEFAULT_SEASON,
    round: Optional[str] = None,
    next: Optional[int] = None,
) -> list[dict]:
    params: dict = {"league": league_id, "season": season}
    if round is not None:
        params["round"] = round
    if next is not None:
        params["next"] = next

    data = _get("/fixtures", params)
    if data is None:
        return _mock_games()

    games = []
    for entry in data.get("response", []):
        fixture = entry.get("fixture", {})
        teams = entry.get("teams", {})
        goals = entry.get("goals", {})
        home = teams.get("home", {})
        away = teams.get("away", {})

        kickoff_raw = fixture.get("date")
        kickoff_at = datetime.fromisoformat(kickoff_raw) if kickoff_raw else None
        locks_at = kickoff_at - timedelta(minutes=30) if kickoff_at else None

        games.append(
            {
                "external_api_id": str(fixture.get("id")),
                "home_team": {
                    "external_api_id": str(home.get("id")),
                    "name": home.get("name"),
                    "crest_url": home.get("logo"),
                },
                "away_team": {
                    "external_api_id": str(away.get("id")),
                    "name": away.get("name"),
                    "crest_url": away.get("logo"),
                },
                "kickoff_at": kickoff_at,
                "status": _map_status((fixture.get("status") or {}).get("short")),
                "home_score": goals.get("home"),
                "away_score": goals.get("away"),
                "locks_at": locks_at,
                "round_name": entry.get("league", {}).get("round"),
            }
        )

    return games


def fetch_standings(league_id: int | str, season: int = _DEFAULT_SEASON) -> list[dict]:
    data = _get("/standings", {"league": league_id, "season": season})
    if data is None:
        return []

    standings = []
    for entry in data.get("response", []):
        groups = ((entry.get("league") or {}).get("standings")) or []
        for group in groups:
            for row in group:
                team = row.get("team", {})
                all_stats = row.get("all", {})
                standings.append(
                    {
                        "team_external_id": str(team.get("id")),
                        "position": row.get("rank"),
                        "played": all_stats.get("played"),
                        "won": all_stats.get("win"),
                        "drawn": all_stats.get("draw"),
                        "lost": all_stats.get("lose"),
                        "points": row.get("points"),
                    }
                )

    return standings
