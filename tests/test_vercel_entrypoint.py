from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path


def test_vercel_entrypoint_imports_from_api_working_directory() -> None:
    project_root = Path(__file__).resolve().parents[1]
    api_dir = project_root / "api"
    original_cwd = Path.cwd()
    sys.path.insert(0, str(api_dir))
    sys.path.insert(0, str(project_root))
    try:
        os.chdir(api_dir)
        module = importlib.import_module("index")
        assert module.app.title == "AI Business Research Agent"
    finally:
        os.chdir(original_cwd)
        sys.path = [path for path in sys.path if path not in {str(api_dir), str(project_root)}]
