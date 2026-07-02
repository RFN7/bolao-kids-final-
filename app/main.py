from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.modules.auth.router import router as auth_router
from app.modules.curiosities.router import router as curiosities_router
from app.modules.families.router import router as families_router
from app.modules.football.router import router as football_router
from app.modules.predictions.router import router as predictions_router
from app.modules.ranking.router import router as ranking_router
from app.shared.exceptions import AppException, app_exception_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.jobs import lock_predictions as lock_job
    from app.modules.curiosities.generator import generate_for_all_games
    from app.modules.football.service import sync_games

    sync_games()
    generate_for_all_games()
    lock_job.start()
    yield


app = FastAPI(title="Bolão Kids API", lifespan=lifespan)

app.add_exception_handler(AppException, app_exception_handler)
app.include_router(auth_router)
app.include_router(families_router)
app.include_router(football_router)
app.include_router(curiosities_router)
app.include_router(predictions_router)
app.include_router(ranking_router)


@app.get("/health")
def health():
    return {"status": "ok"}
