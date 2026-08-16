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
