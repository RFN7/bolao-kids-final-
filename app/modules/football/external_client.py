from datetime import date, datetime, timedelta, timezone


def fetch_games() -> dict:
    now = datetime.now(timezone.utc)
    today = date.today()

    return {
        "teams": [
            {
                "external_api_id": "team_fla",
                "name": "Flamengo",
                "short_name": "FLA",
                "crest_url": None,
                "country": "Brazil",
            },
            {
                "external_api_id": "team_pal",
                "name": "Palmeiras",
                "short_name": "PAL",
                "crest_url": None,
                "country": "Brazil",
            },
            {
                "external_api_id": "team_cor",
                "name": "Corinthians",
                "short_name": "COR",
                "crest_url": None,
                "country": "Brazil",
            },
            {
                "external_api_id": "team_sao",
                "name": "São Paulo",
                "short_name": "SAO",
                "crest_url": None,
                "country": "Brazil",
            },
        ],
        "competition": {
            "external_api_id": "comp_brasileirao_2026",
            "name": "Brasileirão 2026",
            "season": "2026",
            "type": "league",
        },
        "round": {
            "name": "Rodada 1",
            "start_date": today,
            "end_date": today + timedelta(days=7),
        },
        "games": [
            {
                "external_api_id": "game_fla_pal_r1",
                "home_team_external_id": "team_fla",
                "away_team_external_id": "team_pal",
                "kickoff_at": now + timedelta(hours=2),
                "status": "scheduled",
                "home_score": None,
                "away_score": None,
                "locks_at": now + timedelta(hours=2) - timedelta(minutes=30),
            },
            {
                "external_api_id": "game_cor_sao_r1",
                "home_team_external_id": "team_cor",
                "away_team_external_id": "team_sao",
                "kickoff_at": now + timedelta(hours=4),
                "status": "scheduled",
                "home_score": None,
                "away_score": None,
                "locks_at": now + timedelta(hours=4) - timedelta(minutes=30),
            },
        ],
    }
