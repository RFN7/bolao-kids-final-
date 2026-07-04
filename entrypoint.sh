#!/bin/bash
set -e
echo "Rodando migrations..."
alembic upgrade head
echo "Migrations concluídas. Iniciando servidor..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
