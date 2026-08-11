from __future__ import annotations

import sys
from pathlib import Path

from salao.core.config import AppPaths


def test_dev_mode_preserves_source_layout(tmp_path) -> None:
    base_dir = tmp_path / "salao"
    paths = AppPaths(base_dir=base_dir, data_dir=tmp_path / "ignored-dev-data")

    assert paths.frozen is False
    assert paths.database_path == base_dir / "salon.db"
    assert paths.documents_dir == tmp_path / "documents"
    assert paths.receipts_dir == tmp_path / "documents" / "receipts"
    assert paths.backups_dir == tmp_path / "backups"


def test_frozen_mode_uses_localappdata_and_creates_runtime_dirs(tmp_path, monkeypatch) -> None:
    local_app_data = tmp_path / "LocalAppData"
    bundle_dir = tmp_path / "bundle"
    exe_dir = tmp_path / "ProgramFiles" / "SalonFlow"
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle_dir), raising=False)
    monkeypatch.setattr(sys, "executable", str(exe_dir / "SalonFlow.exe"), raising=False)

    paths = AppPaths()

    assert paths.frozen is True
    assert paths.base_dir == bundle_dir
    assert paths.install_dir == exe_dir
    assert paths.user_data_dir == local_app_data / "SalonFlow"
    assert paths.database_path == local_app_data / "SalonFlow" / "salon.db"
    assert paths.receipts_dir == local_app_data / "SalonFlow" / "documents" / "receipts"
    assert paths.backups_dir == local_app_data / "SalonFlow" / "backups"
    assert paths.logs_dir == local_app_data / "SalonFlow" / "logs"
    assert paths.user_data_dir.exists()
    assert paths.receipts_dir.exists()
    assert paths.backups_dir.exists()
    assert paths.logs_dir.exists()


def test_resolve_user_file_prefers_existing_runtime_file(tmp_path) -> None:
    data_dir = tmp_path / "data"
    base_dir = tmp_path / "bundle"
    paths = AppPaths(base_dir=base_dir, data_dir=data_dir)
    logo_path = data_dir / "logo.png"
    logo_path.write_text("logo", encoding="utf-8")

    resolved = paths.resolve_user_file("logo.png")

    assert resolved == logo_path
