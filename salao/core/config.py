from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .version import APP_NAME, APP_VERSION


def _default_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            return Path(meipass).resolve()
    return Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class AppPaths:
    base_dir: Path = field(default_factory=_default_base_dir)
    data_dir: Path | None = None
    app_name: str = APP_NAME
    app_version: str = APP_VERSION

    def __post_init__(self) -> None:
        base_dir = Path(self.base_dir)
        object.__setattr__(self, "base_dir", base_dir)
        resolved_data_dir = Path(self.data_dir) if self.data_dir is not None else self._default_data_dir()
        object.__setattr__(self, "data_dir", resolved_data_dir)
        self.ensure_runtime_dirs()

    @property
    def frozen(self) -> bool:
        return bool(getattr(sys, "frozen", False))

    @property
    def project_dir(self) -> Path:
        if self.frozen:
            return self.install_dir
        return self.base_dir.parent

    @property
    def install_dir(self) -> Path:
        if self.frozen:
            return Path(sys.executable).resolve().parent
        return self.project_dir

    @property
    def user_data_dir(self) -> Path:
        return Path(self.data_dir)

    @property
    def database_path(self) -> Path:
        if self.frozen:
            return self.user_data_dir / "salon.db"
        return self.base_dir / "salon.db"

    @property
    def assets_dir(self) -> Path:
        return self.base_dir / "assets"

    @property
    def hero_image_path(self) -> Path:
        return self.assets_dir / "undo.jpeg"

    @property
    def documents_dir(self) -> Path:
        if self.frozen:
            return self.user_data_dir / "documents"
        return self.project_dir / "documents"

    @property
    def receipts_dir(self) -> Path:
        return self.documents_dir / "receipts"

    @property
    def backups_dir(self) -> Path:
        if self.frozen:
            return self.user_data_dir / "backups"
        return self.project_dir / "backups"

    @property
    def logs_dir(self) -> Path:
        if self.frozen:
            return self.user_data_dir / "logs"
        return self.project_dir / "logs"

    def ensure_runtime_dirs(self) -> None:
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        self.receipts_dir.mkdir(parents=True, exist_ok=True)
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def resolve_user_file(self, raw_path: str | Path) -> Path:
        candidate = Path(raw_path).expanduser()
        if candidate.is_absolute():
            return candidate
        for root in (self.user_data_dir, self.documents_dir, self.project_dir, self.install_dir, self.base_dir):
            resolved = root / candidate
            if resolved.exists():
                return resolved
        return self.user_data_dir / candidate

    def _default_data_dir(self) -> Path:
        if not self.frozen:
            return self.project_dir
        env_dir = os.environ.get("SALONFLOW_DATA_DIR", "").strip()
        if env_dir:
            return Path(env_dir).expanduser()
        local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
        if local_app_data:
            return Path(local_app_data) / self.app_name
        return self.install_dir / "data"
