import os
import subprocess
import sys
from pathlib import Path


def test_main_starts() -> None:
    project_dir = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "main.py"],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "MULTIAGENTAI_FORCE_CONSOLE": "1"},
        cwd=project_dir,
    )
    assert result.returncode == 0
    assert "Projeto inicializado com sucesso." in result.stdout
