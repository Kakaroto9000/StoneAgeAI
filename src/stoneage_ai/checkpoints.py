"""
Find saved model checkpoints under ``models/``.

Layout written by training (see ``agent.train``):
    models/runs/<run>/games_0010000.pth          every CHECKPOINT_EVERY games
    models/runs/<run>/games_0000250_stopped.pth  when training is stopped (Ctrl+C)
    models/runs/<run>/best.pth                   at each new learner VP record
    models/*.pth                                 older checkpoints (before run folders)

Shared by the training tracker and the web UI's model picker.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from stoneage_ai.paths import MODELS_DIR

_GAMES_RE = re.compile(r"^games_(\d+)(_stopped)?\.pth$")


def describe_checkpoint(path: Path, models_dir: Path = MODELS_DIR) -> Dict:
    """Metadata for one .pth file.

    Returns a dict with:
        id        path relative to models/, with forward slashes (use as an identifier)
        path      absolute Path
        run       run folder name, or None for legacy files in models/
        kind      "periodic" | "stopped" | "best" | "legacy"
        games     games trained when saved (int), or None if unknown
        modified  last-modified time as ISO string
        size_kb   file size in KB
    """
    path = Path(path)
    rel = path.relative_to(models_dir)
    run = rel.parts[1] if len(rel.parts) == 3 and rel.parts[0] == "runs" else None
    match = _GAMES_RE.match(path.name)
    if run is None:
        kind, games = "legacy", None
    elif match:
        kind, games = ("stopped" if match.group(2) else "periodic"), int(match.group(1))
    elif path.name == "best.pth":
        kind, games = "best", None
    else:
        kind, games = "other", None
    stat = path.stat()
    return {
        "id": rel.as_posix(),
        "path": path,
        "run": run,
        "kind": kind,
        "games": games,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        "size_kb": round(stat.st_size / 1024),
    }


def list_checkpoints(models_dir: Path = MODELS_DIR, run: Optional[str] = None) -> List[Dict]:
    """All checkpoints, newest run first, then by games trained within a run.

    Args:
        run: only list checkpoints from this run folder name.
    """
    models_dir = Path(models_dir)
    if not models_dir.exists():
        return []
    files = list((models_dir / "runs").glob("*/*.pth")) if (models_dir / "runs").exists() else []
    if run is None:
        files += list(models_dir.glob("*.pth"))
    items = [describe_checkpoint(f, models_dir) for f in files]
    if run is not None:
        items = [c for c in items if c["run"] == run]
    kind_order = {"periodic": 0, "stopped": 1, "best": 2, "other": 3, "legacy": 4}
    # Newest run first (folder names are timestamps); inside a run: periodic by games,
    # then stopped, then best. Legacy files in models/ come last.
    runs = sorted({c["run"] for c in items if c["run"]}, reverse=True)
    ordered = []
    for r in runs:
        group = [c for c in items if c["run"] == r]
        group.sort(key=lambda c: (kind_order[c["kind"]], c["games"] or 0))
        ordered += group
    ordered += sorted((c for c in items if c["run"] is None), key=lambda c: c["id"])
    return ordered


def latest_checkpoint(models_dir: Path = MODELS_DIR) -> Optional[Path]:
    """The most recently saved periodic/stopped checkpoint (else any), or None if there are none."""
    items = list_checkpoints(models_dir)
    preferred = [c for c in items if c["kind"] in ("periodic", "stopped")] or items
    if not preferred:
        return None
    return max(preferred, key=lambda c: c["path"].stat().st_mtime)["path"]


def resolve_checkpoint(checkpoint_id: str, models_dir: Path = MODELS_DIR) -> Path:
    """Turn an id from ``list_checkpoints`` back into a path, refusing anything outside models/."""
    models_dir = Path(models_dir).resolve()
    path = (models_dir / checkpoint_id).resolve()
    if models_dir not in path.parents or path.suffix != ".pth" or not path.is_file():
        raise ValueError(f"Unknown checkpoint: {checkpoint_id}")
    return path
