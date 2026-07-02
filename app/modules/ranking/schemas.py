import uuid

from pydantic import BaseModel


class FamilyInfo(BaseModel):
    id: uuid.UUID
    display_name: str


class FamilyRankingEntry(BaseModel):
    position: int
    family: FamilyInfo
    total_points_family: int


class RankingResponse(BaseModel):
    ranking: list[FamilyRankingEntry]
    total: int


class RankingHistoryEntry(BaseModel):
    round: str
    position: int
    total_points_family: int


class RankingHistoryResponse(BaseModel):
    history: list[RankingHistoryEntry]
