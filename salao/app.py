from __future__ import annotations

from .core.config import AppPaths
from .desktop.main_window import run_desktop_app


def run() -> None:
    run_desktop_app(AppPaths())
