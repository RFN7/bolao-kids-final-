from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class TeamResponse(BaseModel):
    id: UUID
    external_api_id: str
    name: str
    short_name: Optional[str] = None
    crest_url: Optional[str] = None

    model_config = {"from_attributes": True}


class CompetitionResponse(BaseModel):
    id: UUID
    name: str
    season: str
    type: str

    model_config = {"from_attributes": True}


class RoundResponse(BaseModel):
    id: UUID
    name: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    model_config = {"from_attributes": True}


class GameResponse(BaseModel):
    id: UUID
    round_id: UUID
    home_team: TeamResponse
    away_team: TeamResponse
    kickoff_at: datetime
    status: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    locks_at: datetime

    model_config = {"from_attributes": True}
