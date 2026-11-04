from alembic import command
from alembic.config import Config


def test_migration_round_trip(tmp_path: object, monkeypatch: object) -> None:
    database = tmp_path / "migrated.db"  # type: ignore[operator]
    monkeypatch.setenv("ASSETMIND_DATABASE_URL", f"sqlite+pysqlite:///{database}")  # type: ignore[attr-defined]
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    command.upgrade(config, "head")
