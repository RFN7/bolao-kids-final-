import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.cache import redis_client
from app.modules.families.models import Family, FamilyStatistics
from app.modules.football.models import Round
from app.modules.ranking.models import RankingSnapshot
from app.modules.ranking.schemas import (
    FamilyInfo,
    FamilyRankingEntry,
    RankingHistoryEntry,
    RankingHistoryResponse,
    RankingResponse,
)
from app.shared.exceptions import AppException

_CACHE_PREFIX = "ranking"
_CACHE_TTL = 60


@dataclass
class _RankingRow:
    position: int
    family_id: uuid.UUID
    display_name: str
    total_points_family: int


def _query_all_entries(db: Session) -> list[_RankingRow]:
    rows = (
        db.query(FamilyStatistics, Family)
        .join(Family, Family.id == FamilyStatistics.family_id)
        .filter(Family.status == "active")
        .order_by(
            FamilyStatistics.total_points_family.desc(),
            FamilyStatistics.exact_hits.desc(),
        )
        .all()
    )
    return [
        _RankingRow(
            position=pos,
            family_id=family.id,
            display_name=family.display_name,
            total_points_family=stats.total_points_family,
        )
        for pos, (stats, family) in enumerate(rows, start=1)
    ]


def get_ranking(db: Session, limit: int = 50, offset: int = 0) -> RankingResponse:
    cache_key = f"{_CACHE_PREFIX}:{limit}:{offset}"
    cached = redis_client.get(cache_key)
    if cached:
        return RankingResponse.model_validate_json(cached)

    all_entries = _query_all_entries(db)
    total = len(all_entries)
    page = all_entries[offset : offset + limit]

    response = RankingResponse(
        ranking=[
            FamilyRankingEntry(
                position=e.position,
                family=FamilyInfo(id=e.family_id, display_name=e.display_name),
                total_points_family=e.total_points_family,
            )
            for e in page
        ],
        total=total,
    )
    redis_client.setex(cache_key, _CACHE_TTL, response.model_dump_json())
    return response


def get_ranking_history(family_id: uuid.UUID, db: Session) -> RankingHistoryResponse:
    family = db.query(Family).filter(Family.id == family_id).first()
    if not family:
        raise AppException("FAMILY_NOT_FOUND", "Família não encontrada", 404)

    rows = (
        db.query(RankingSnapshot, Round)
        .join(Round, Round.id == RankingSnapshot.round_id)
        .filter(RankingSnapshot.family_id == family_id)
        .order_by(RankingSnapshot.created_at.asc())
        .all()
    )

    history = [
        RankingHistoryEntry(
            round=round_.name,
            position=snapshot.position,
            total_points_family=snapshot.total_points_family,
        )
        for snapshot, round_ in rows
    ]
    return RankingHistoryResponse(history=history)


def save_ranking_snapshot(round_id: uuid.UUID) -> None:
    from app.database import SessionLocal

    db: Session = SessionLocal()
    try:
        entries = _query_all_entries(db)
        for entry in entries:
            existing = (
                db.query(RankingSnapshot)
                .filter(
                    RankingSnapshot.round_id == round_id,
                    RankingSnapshot.family_id == entry.family_id,
                )
                .first()
            )
            if existing:
                existing.position = entry.position
                existing.total_points_family = entry.total_points_family
            else:
                db.add(
                    RankingSnapshot(
                        round_id=round_id,
                        family_id=entry.family_id,
                        position=entry.position,
                        total_points_family=entry.total_points_family,
                    )
                )
        db.commit()
        for key in redis_client.scan_iter(f"{_CACHE_PREFIX}:*"):
            redis_client.delete(key)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
