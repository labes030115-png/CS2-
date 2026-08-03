from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import URL


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_TABLES = {
    "taxonomy_groups",
    "collections",
    "collection_group_memberships",
    "assets",
    "source_item_mappings",
    "price_snapshots",
}


def alembic_config() -> Config:
    config = Config(PROJECT_ROOT / "alembic.ini")
    config.set_main_option(
        "script_location",
        str(PROJECT_ROOT / "backend" / "alembic"),
    )
    return config


def test_initial_migration_upgrades_and_downgrades_clean_database(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "migration.sqlite3"
    monkeypatch.setenv("CS2_DATABASE_PATH", str(database_path))
    config = alembic_config()

    command.upgrade(config, "head")

    engine = create_engine(
        URL.create("sqlite+pysqlite", database=str(database_path)),
    )
    assert APP_TABLES.issubset(inspect(engine).get_table_names())
    constraints = {
        constraint["name"]: constraint["sqltext"]
        for constraint in inspect(engine).get_check_constraints(
            "price_snapshots"
        )
    }
    assert constraints["ck_snapshot_metric"] == "metric = 'lowest_listing'"
    with engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA user_version").scalar_one() == 1
        assert connection.exec_driver_sql(
            "SELECT version_num FROM alembic_version"
        ).scalar_one() == "0001_initial"

    command.downgrade(config, "base")

    assert APP_TABLES.isdisjoint(inspect(engine).get_table_names())
    with engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA user_version").scalar_one() == 0

    engine.dispose()


def test_revision_template_generates_valid_python(tmp_path: Path) -> None:
    versions_path = tmp_path / "versions"
    versions_path.mkdir()
    config = alembic_config()
    config.set_main_option("version_locations", str(versions_path))

    generated = command.revision(
        config,
        message="template smoke test",
        rev_id="template_smoke",
    )

    generated_path = Path(generated.path)
    source = generated_path.read_text(encoding="utf-8")
    assert generated_path.parent == versions_path
    assert "revision: str = 'template_smoke'" in source
    assert "def upgrade() -> None:" in source
    assert "def downgrade() -> None:" in source
    compile(source, str(generated_path), "exec")
