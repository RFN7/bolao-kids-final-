import os

# Garante que as env vars existam antes de qualquer import de app.*
# Dentro do Docker as vars já estão setadas pelo docker-compose; setdefault não sobrescreve.
# Fora do Docker, aponta para localhost (serviços com porta exposta).
os.environ.setdefault("DATABASE_URL", "postgresql://bolao_kids:local_dev@localhost:5432/bolao_kids")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET", "test_secret_for_tests_only")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("FOOTBALL_API_KEY", "")
