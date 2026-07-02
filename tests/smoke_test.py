#!/usr/bin/env python3
"""
Smoke test end-to-end do backend Bolão Kids.
Executa os 10 passos do checklist de release (16_DEPLOY.md §7).

Uso:
    python tests/smoke_test.py [BASE_URL]

    BASE_URL padrão: http://localhost:8000
"""

import sys
import uuid
import json
import time
from datetime import datetime

try:
    import httpx
except ImportError:
    print("ERRO: httpx não instalado. Execute: pip install httpx")
    sys.exit(1)

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8000"
EMAIL = f"smoke_{uuid.uuid4().hex[:8]}@teste.com"
PASSWORD = "Smoke@1234"

_RESULTS: list[tuple[int, str, bool, str]] = []


def check(step: int, name: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    _RESULTS.append((step, name, ok, detail))
    badge = "\033[32mPASS\033[0m" if ok else "\033[31mFAIL\033[0m"
    line = f"  [{badge}] Passo {step:02d}: {name}"
    if detail:
        line += f"\n         {detail}"
    print(line)
    if not ok:
        print(f"         Detalhe: {detail}")


def _post(path: str, body: dict, headers: dict | None = None) -> httpx.Response:
    return httpx.post(f"{BASE}{path}", json=body, headers=headers or {}, timeout=10)


def _get(path: str, headers: dict | None = None, params: dict | None = None) -> httpx.Response:
    return httpx.get(f"{BASE}{path}", headers=headers or {}, params=params or {}, timeout=10)


def run() -> int:
    print(f"\nBolão Kids — Smoke Test")
    print(f"Target : {BASE}")
    print(f"Email  : {EMAIL}")
    print(f"{'─' * 55}")

    token = ""
    family_id = ""
    game_id = ""

    # ------------------------------------------------------------------
    # Passo 1 — Health check
    # ------------------------------------------------------------------
    try:
        r = _get("/health")
        ok = r.status_code == 200 and r.json().get("status") == "ok"
        check(1, "Health check", ok, f"status={r.status_code} body={r.text[:80]}")
    except Exception as e:
        check(1, "Health check", False, str(e))
        print("\nServidor inacessível. Encerrando.")
        return _summary()

    # ------------------------------------------------------------------
    # Passo 2 — Registrar usuário
    # ------------------------------------------------------------------
    try:
        r = _post("/auth/register", {"name": "Romero Silva", "email": EMAIL, "password": PASSWORD})
        ok = r.status_code == 201 and "id" in r.json()
        check(2, "Registrar usuário", ok, f"status={r.status_code} email={EMAIL}")
    except Exception as e:
        check(2, "Registrar usuário", False, str(e))

    # ------------------------------------------------------------------
    # Passo 3 — Login e salvar token
    # ------------------------------------------------------------------
    try:
        r = _post("/auth/login", {"identifier": EMAIL, "password": PASSWORD})
        ok = r.status_code == 200 and "access_token" in r.json()
        if ok:
            token = r.json()["access_token"]
        check(3, "Login e salvar access_token", ok, f"status={r.status_code} token={'ok' if token else 'missing'}")
    except Exception as e:
        check(3, "Login e salvar access_token", False, str(e))

    if not token:
        print("\nToken ausente — impossível continuar.")
        return _summary()

    HDR = {"Authorization": f"Bearer {token}"}

    # ------------------------------------------------------------------
    # Passo 4 — Consentimento LGPD
    # ------------------------------------------------------------------
    try:
        r = _post("/auth/consent", {"consent_version": "1.0"}, HDR)
        ok = r.status_code == 200 and "consented_at" in r.json()
        check(4, "Consentimento LGPD", ok, f"status={r.status_code}")
    except Exception as e:
        check(4, "Consentimento LGPD", False, str(e))

    # ------------------------------------------------------------------
    # Passo 5 — Criar família
    # ------------------------------------------------------------------
    try:
        r = _post("/families", {"child": {"name": "Noah"}, "display_name": "Família Romero"}, HDR)
        ok = r.status_code == 201 and "id" in r.json()
        if ok:
            family_id = r.json()["id"]
        check(5, "Criar família", ok, f"status={r.status_code} family_id={family_id[:8]}..." if family_id else f"status={r.status_code}")
    except Exception as e:
        check(5, "Criar família", False, str(e))

    # ------------------------------------------------------------------
    # Passo 6 — Ver jogos disponíveis
    # ------------------------------------------------------------------
    scheduled_game_id = ""
    try:
        r = _get("/games")
        games = r.json()
        ok = r.status_code == 200 and isinstance(games, list) and len(games) > 0
        if ok:
            # Preferir jogo ainda agendado para poder fazer palpite
            for g in games:
                if g.get("status") == "scheduled":
                    scheduled_game_id = g["id"]
                    break
            game_id = scheduled_game_id or games[0]["id"]
        check(6, "Ver jogos disponíveis", ok, f"status={r.status_code} total={len(games) if ok else 'err'}")
    except Exception as e:
        check(6, "Ver jogos disponíveis", False, str(e))

    # ------------------------------------------------------------------
    # Passo 7 — Curiosidades do primeiro jogo
    # ------------------------------------------------------------------
    try:
        r = _get(f"/games/{game_id}/curiosities")
        data = r.json()
        ok = r.status_code == 200 and len(data.get("curiosities", [])) == 2
        check(7, "Curiosidades do jogo", ok,
              f"status={r.status_code} roles={[c['role'] for c in data.get('curiosities', [])]}")
    except Exception as e:
        check(7, "Curiosidades do jogo", False, str(e))

    # ------------------------------------------------------------------
    # Passo 8 — Registrar os 3 palpites (requer jogo agendado)
    # ------------------------------------------------------------------
    pred_target = scheduled_game_id or game_id
    preds_ok = True
    try:
        for author_type, home, away in [("pai", 2, 1), ("filho", 3, 2), ("familia", 2, 1)]:
            r = _post("/predictions", {
                "family_id": family_id,
                "game_id": pred_target,
                "author_type": author_type,
                "home_score_pred": home,
                "away_score_pred": away,
            }, HDR)
            if r.status_code != 201:
                preds_ok = False
                check(8, f"Palpite {author_type}", False, f"status={r.status_code} body={r.text[:120]}")
        if preds_ok:
            check(8, "Registrar 3 palpites (pai/filho/familia)", True, f"game_id={pred_target[:8]}...")
    except Exception as e:
        check(8, "Registrar 3 palpites", False, str(e))
        preds_ok = False

    # ------------------------------------------------------------------
    # Passo 9 — Confirmar is_complete=true
    # ------------------------------------------------------------------
    try:
        r = _get(f"/games/{pred_target}/predictions/me", HDR, {"family_id": family_id})
        data = r.json()
        ok = r.status_code == 200 and data.get("is_complete") is True
        check(9, "Confirmar is_complete=true", ok,
              f"status={r.status_code} is_complete={data.get('is_complete')}")
    except Exception as e:
        check(9, "Confirmar is_complete=true", False, str(e))

    # ------------------------------------------------------------------
    # Passo 10 — Simular resultado + apply_results + ranking
    # ------------------------------------------------------------------
    try:
        # Aplica resultado via script direto (necessita acesso ao DB)
        import os
        db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://bolao_kids:local_dev@localhost:5432/bolao_kids",
        )
        from sqlalchemy import create_engine, text as sqlt

        engine = create_engine(db_url)
        with engine.connect() as conn:
            conn.execute(
                sqlt("UPDATE games SET status='finished', home_score=2, away_score=1 WHERE id=:id"),
                {"id": uuid.UUID(pred_target)},
            )
            conn.commit()

        # Importa e chama apply_results
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
        os.environ.setdefault("JWT_SECRET", "smoke_test_secret")
        os.environ.setdefault("ENVIRONMENT", "smoke")
        os.environ.setdefault("FOOTBALL_API_KEY", "")

        from app.modules.scoring.service import apply_results
        apply_results(uuid.UUID(pred_target))

        # Consulta ranking
        r = _get("/ranking", HDR)
        data = r.json()
        ok = r.status_code == 200 and data.get("total", 0) >= 1
        top = data["ranking"][0] if data.get("ranking") else {}
        check(
            10,
            "Simular resultado → apply_results → ranking",
            ok,
            f"status={r.status_code} pos1={top.get('family', {}).get('display_name','?')} pts={top.get('total_points_family','?')}",
        )
    except Exception as e:
        check(10, "Simular resultado + ranking", False, str(e))

    return _summary()


def _summary() -> int:
    total = len(_RESULTS)
    passed = sum(1 for _, _, ok, _ in _RESULTS if ok)
    failed = total - passed

    print(f"\n{'─' * 55}")
    print(f"Resultado: {passed}/{total} passos passando")
    if failed:
        print(f"\nFalhas:")
        for step, name, ok, detail in _RESULTS:
            if not ok:
                print(f"  Passo {step:02d}: {name}")
                print(f"    {detail}")
    print()

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
