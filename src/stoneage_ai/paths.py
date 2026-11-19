"""Project-wide filesystem paths, resolved relative to the repository root."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = PROJECT_ROOT / "models"
