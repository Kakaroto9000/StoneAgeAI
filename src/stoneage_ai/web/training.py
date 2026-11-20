"""
Start, stop and watch training runs from the web UI.

Training runs as a separate ``python train.py`` process (so the web server stays
responsive and a page reload doesn't touch it). Its console output goes to
``models/runs/<run>/train.log``. Progress comes from the files training writes
anyway, so runs started from a terminal show up too:

    config.json      how the run was started (resume, opponents, start/finish time)
    progress.jsonl   one line of averages per 100 games
    checkpoints.csv  older runs without progress.jsonl fall back to this (one row per 10k games)

Stopping creates ``models/runs/<run>/STOP``; training finishes the current game,
saves a ``games_<n>_stopped.pth`` checkpoint and exits.
"""

import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from stoneage_ai.agent.tracking import read_checkpoint_log
from stoneage_ai.checkpoints import list_checkpoints
from stoneage_ai.paths import MODELS_DIR, PROJECT_ROOT

RUNS_DIR = MODELS_DIR / "runs"
TRAIN_SCRIPT = PROJECT_ROOT / "train.py"
LOG_TAIL_LINES = 40
ACTIVE_SECONDS = 120  # a run whose progress changed this recently counts as "probably running"


class TrainingError(RuntimeError):
    pass


_lock = threading.Lock()
_proc: Optional[subprocess.Popen] = None
_proc_run: Optional[str] = None


def _running() -> bool:
    return _proc is not None and _proc.poll() is None


def start(resume: Optional[Path], opponents: List[str], tensorboard: bool = True) -> str:
    """Launch ``train.py`` in the background and return the new run's name.

    ``opponents`` are train.py specs: "self", "random" or an absolute checkpoint path.
    """
    global _proc, _proc_run
    with _lock:
        if _running():
            raise TrainingError(f"Training is already running ({_proc_run}). Stop it first.")
        run = f"{datetime.now():%Y-%m-%d_%H-%M-%S}"
        run_dir = RUNS_DIR / run
        run_dir.mkdir(parents=True, exist_ok=True)
        cmd = [sys.executable, "-u", str(TRAIN_SCRIPT), "--run-name", run,
               "--opponents", *[str(o) for o in opponents]]
        if resume is not None:
            cmd += ["--resume", str(resume)]
        if not tensorboard:
            cmd.append("--no-tensorboard")
        # The child gets its own copy of the handle; closing ours right away means the
        # server never holds train.log open (so the run folder can be deleted on Windows).
        with open(run_dir / "train.log", "a", encoding="utf-8", errors="replace") as log:
            _proc = subprocess.Popen(cmd, cwd=PROJECT_ROOT, stdout=log, stderr=subprocess.STDOUT,
                                     env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        _proc_run = run
        return run


def stop(run: Optional[str] = None) -> str:
    """Ask a run to stop after its current game (defaults to the one this server started)."""
    run = run or _proc_run
    if run is None:
        raise TrainingError("No training run to stop.")
    run_dir = _run_dir(run)
    (run_dir / "STOP").touch()
    return run


def _run_dir(run: str) -> Path:
    path = (RUNS_DIR / run).resolve()
    if path.parent != RUNS_DIR.resolve() or not path.is_dir():
        raise TrainingError(f"Unknown run: {run}")
    return path


def _read_json(path: Path) -> Optional[Dict]:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def _num(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return None if value != value else value


def _progress(run_dir: Path) -> Dict:
    """Averages over time: progress.jsonl, else checkpoints.csv (coarser)."""
    path = run_dir / "progress.jsonl"
    if path.exists():
        points = []
        with open(path) as f:
            for line in f:
                try:
                    points.append(json.loads(line))
                except ValueError:  # a line being written right now
                    pass
        return {"source": "progress", "points": points}
    rows = read_checkpoint_log(run_dir)
    points = [{k: (_num(v) if k not in ("checkpoint", "saved_at") else v) for k, v in r.items()}
              for r in rows]
    return {"source": "checkpoints", "points": points}


def _log_tail(run_dir: Path) -> List[str]:
    path = run_dir / "train.log"
    if not path.exists():
        return []
    with open(path, "rb") as f:
        f.seek(0, 2)
        f.seek(max(0, f.tell() - 16_000))
        text = f.read().decode("utf-8", errors="replace")
    # Progress bars and Windows line endings: keep the last state of each line.
    lines = [line.split("\r")[-1] for line in text.splitlines()]
    return lines[-LOG_TAIL_LINES:]


def _last_update(run_dir: Path) -> Optional[float]:
    times = [p.stat().st_mtime for p in run_dir.iterdir() if p.is_file()]
    return max(times) if times else None


def _run_summary(run_dir: Path) -> Dict:
    config = _read_json(run_dir / "config.json") or {}
    last = _last_update(run_dir)
    managed = _running() and run_dir.name == _proc_run
    finished = config.get("finished_at") is not None
    return {
        "name": run_dir.name,
        "opponents": config.get("opponents"),
        "resume": config.get("resume"),
        "started_at": config.get("started_at"),
        "finished_at": config.get("finished_at"),
        "last_update": datetime.fromtimestamp(last).isoformat(timespec="seconds") if last else None,
        # Started here and still alive, or (started elsewhere) not finished and recently updated.
        "running": managed or (not finished and last is not None
                               and time.time() - last < ACTIVE_SECONDS),
        "managed": managed,
        "stopping": (run_dir / "STOP").exists(),
    }


def status(run: Optional[str] = None) -> Dict:
    """Payload for GET /api/training: all runs plus the details of one (default: newest)."""
    runs_dirs = sorted((p for p in RUNS_DIR.iterdir() if p.is_dir()), reverse=True) \
        if RUNS_DIR.exists() else []
    runs = [_run_summary(p) for p in runs_dirs]
    if run is None:
        run = _proc_run if _running() else (runs[0]["name"] if runs else None)
    detail = None
    if run is not None:
        run_dir = _run_dir(run)
        detail = {
            **_run_summary(run_dir),
            "config": _read_json(run_dir / "config.json"),
            "progress": _progress(run_dir),
            "checkpoints": [{"id": c["id"], "kind": c["kind"], "games": c["games"]}
                            for c in list_checkpoints(run=run)],
            "log": _log_tail(run_dir),
            "exit_code": _proc.poll() if _proc is not None and run == _proc_run else None,
        }
    return {"active": _proc_run if _running() else None, "runs": runs, "run": detail}
