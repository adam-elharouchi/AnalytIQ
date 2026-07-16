"""
tests/unit/test_migrations_deploy_step.py — H-8: migrations as a gated deploy step.

Migrations historically ran on every worker boot. They can now run once per deploy
via `python db_migrate.py` (Render preDeployCommand), with boot-time migration
gated behind config.RUN_MIGRATIONS_ON_BOOT (default True). The CLI must surface a
failed migration as a non-zero exit so a broken migration blocks the deploy.
"""
from unittest.mock import MagicMock, patch

import config
import core.factory as factory
import db_migrate


class TestBootGate:
    def test_boot_migrations_skipped_when_flag_off(self, monkeypatch):
        monkeypatch.setattr(config, "RUN_MIGRATIONS_ON_BOOT", False)
        with patch("core.database.get_db_connection") as get_conn:
            factory.run_migrations(MagicMock())
        get_conn.assert_not_called()

    def test_boot_migrations_run_when_flag_on(self, monkeypatch):
        monkeypatch.setattr(config, "RUN_MIGRATIONS_ON_BOOT", True)
        app = MagicMock()
        with patch("core.database.get_db_connection") as get_conn, patch(
            "db_migrate.run_migrations"
        ) as run:
            factory.run_migrations(app)
        get_conn.assert_called_once()
        run.assert_called_once()


class TestApplyReturnsFailures:
    def _cursor(self):
        cur = MagicMock()
        cur.__enter__ = lambda s: cur
        cur.__exit__ = lambda *a: False
        return cur

    def test_returns_empty_on_success(self, tmp_path, monkeypatch):
        # No migration files -> nothing pending -> no failures.
        monkeypatch.setattr(db_migrate, "_MIGRATIONS_DIR", str(tmp_path))
        conn = MagicMock()
        conn.cursor.return_value = self._cursor()
        assert db_migrate._apply_pending_migrations(conn) == []

    def test_returns_failed_filename_when_a_migration_errors(self, tmp_path, monkeypatch):
        (tmp_path / "001_bad.sql").write_text("THIS IS NOT VALID SQL;")
        monkeypatch.setattr(db_migrate, "_MIGRATIONS_DIR", str(tmp_path))

        # cursor: tracking-table create OK, "already applied?" -> None (not applied),
        # then executing the bad SQL raises.
        def _execute(sql, params=None):
            if "THIS IS NOT VALID SQL" in str(sql):
                raise Exception("syntax error")

        cur = self._cursor()
        cur.execute.side_effect = _execute
        cur.fetchone.return_value = None
        conn = MagicMock()
        conn.cursor.return_value = cur

        failed = db_migrate._apply_pending_migrations(conn)
        assert failed == ["001_bad.sql"]


class TestCli:
    def test_cli_exits_nonzero_on_failure(self):
        with patch("psycopg2.connect", return_value=MagicMock()), patch(
            "core.database.get_db_params", return_value={}
        ), patch("db_migrate.run_migrations", return_value=["001_bad.sql"]):
            assert db_migrate._run_cli() == 1

    def test_cli_exits_zero_on_success(self):
        with patch("psycopg2.connect", return_value=MagicMock()), patch(
            "core.database.get_db_params", return_value={}
        ), patch("db_migrate.run_migrations", return_value=[]):
            assert db_migrate._run_cli() == 0

    def test_cli_exits_nonzero_when_connection_fails(self):
        with patch("core.database.get_db_params", return_value={}), patch(
            "psycopg2.connect", side_effect=Exception("db down")
        ):
            assert db_migrate._run_cli() == 1
