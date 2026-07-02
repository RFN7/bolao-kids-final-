from pydantic import BaseModel

from app.modules.football.schemas import TeamResponse


class CuriosityResponse(BaseModel):
    role: str
    team: TeamResponse
    text: str
    stat_source: str

    model_config = {"from_attributes": True}


class CuriositiesResponse(BaseModel):
    curiosities: list[CuriosityResponse]
