from pathlib import Path


def test_resolve_log_dir_uses_writable_location(tmp_path):
    from project.settings import resolve_log_dir

    assert resolve_log_dir(tmp_path) == tmp_path / 'logs'

    # If the directory is not writable, we should fall back to a writable runtime path.
    readonly = tmp_path / 'readonly'
    readonly.mkdir()
    readonly.chmod(0o555)
    try:
        result = resolve_log_dir(readonly)
        assert result != readonly
        assert result.is_dir()
    finally:
        readonly.chmod(0o755)


def test_build_database_config_falls_back_to_sqlite_when_psycopg_unavailable(monkeypatch):
    from project.settings import build_database_config

    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:pass@host:5432/db')
    config = build_database_config(psycopg_available=False)

    assert config['ENGINE'] == 'django.db.backends.sqlite3'
    assert config['NAME'].endswith('db.sqlite3')
