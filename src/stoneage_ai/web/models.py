"""
Which trained model the AI seats use: the picker list and a small policy cache.

Model ids are checkpoint ids from ``stoneage_ai.checkpoints`` (paths relative to
models/, e.g. ``runs/2026-11-18_21-05-33/games_0010000.pth``) or ``"random"``.
A default given to ``play.py --model`` that lives outside models/ gets its
absolute path as id; it is only reachable because it is the server default.
"""

import threading
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from stoneage_ai.agent.policy import DEFAULT_MODEL, GreedyPolicy
from stoneage_ai.checkpoints import describe_checkpoint, list_checkpoints, resolve_checkpoint
from stoneage_ai.game.game import Game
from stoneage_ai.paths import MODELS_DIR

RANDOM = "random"
CACHE_SIZE = 4  # loaded networks kept in memory

_lock = threading.Lock()
_policies: "OrderedDict[Tuple[str, Optional[float]], GreedyPolicy]" = OrderedDict()
_compat: Dict[Tuple[str, str], bool] = {}  # (id, modified) -> shapes match
_num_actions: Optional[int] = None
_default_id = RANDOM
_default_path: Optional[Path] = None


class UnknownModel(ValueError):
    pass


def num_actions() -> int:
    global _num_actions
    if _num_actions is None:
        probe = Game()
        probe.reset()
        _num_actions = probe.action_system.NUM_ACTIONS
    return _num_actions


def _id_for(path: Optional[Path]) -> str:
    if path is None:
        return RANDOM
    try:
        return Path(path).resolve().relative_to(MODELS_DIR.resolve()).as_posix()
    except ValueError:
        return str(Path(path).resolve())


def configure_default(model_path: Optional[Path] = DEFAULT_MODEL) -> None:
    """Set the model used when a new game doesn't name one (None = random)."""
    global _default_id, _default_path
    with _lock:
        _default_id, _default_path = _id_for(model_path), model_path
        _policies.clear()


def default_id() -> str:
    return _default_id


def _run_label(run: str) -> str:
    try:
        return f"Run {datetime.strptime(run, '%Y-%m-%d_%H-%M-%S'):%Y-%m-%d %H:%M}"
    except ValueError:
        return f"Run {run}"


def label_for(ckpt: Dict) -> str:
    """Friendly name for an entry of ``list_checkpoints()``."""
    name = Path(ckpt["id"]).name
    if ckpt["run"] is None:
        return f"{name} (legacy)"
    run = _run_label(ckpt["run"])
    games = ckpt["games"]
    if ckpt["kind"] == "periodic":
        return f"{run} · {games:,} games"
    if ckpt["kind"] == "stopped":
        return f"{run} · stopped at {games:,} games"
    if ckpt["kind"] == "best":
        return f"{run} · best"
    return f"{run} · {name}"


def _compatible(ckpt: Dict) -> bool:
    key = (ckpt["id"], ckpt["modified"])
    if key not in _compat:
        _compat[key] = GreedyPolicy.is_compatible(ckpt["path"], num_actions())
    return _compat[key]


def _entry(ckpt: Dict) -> Dict:
    ok = _compatible(ckpt)
    label = label_for(ckpt)
    return {
        "id": ckpt["id"],
        "label": label if ok else f"{label}: incompatible, plays random",
        "run": ckpt["run"],
        "kind": ckpt["kind"],
        "games": ckpt["games"],
        "modified": ckpt["modified"],
        "size_kb": ckpt["size_kb"],
        "compatible": ok,
        "default": ckpt["id"] == _default_id,
    }


def list_models() -> Dict:
    """Payload for GET /api/models: every checkpoint plus random moves."""
    with _lock:
        models = [_entry(c) for c in list_checkpoints()]
        ids = {m["id"] for m in models}
        if _default_id != RANDOM and _default_id not in ids:
            # play.py --model pointed outside models/ (or at a missing file).
            path = Path(_default_path)
            if path.is_file():
                ckpt = {"id": _default_id, "path": path, "run": None, "kind": "other",
                        "games": None, "size_kb": round(path.stat().st_size / 1024),
                        "modified": datetime.fromtimestamp(path.stat().st_mtime)
                                            .isoformat(timespec="seconds")}
                entry = _entry(ckpt)
                entry["label"] = f"{path.name} (--model)" + ("" if entry["compatible"]
                                                            else ": incompatible, plays random")
            else:
                entry = {"id": _default_id, "label": f"{path.name}: not found, plays random",
                         "run": None, "kind": "other", "games": None, "modified": None,
                         "size_kb": None, "compatible": False, "default": True}
            models.insert(0, entry)
        models.append({"id": RANDOM, "label": "Random moves", "run": None, "kind": "random",
                       "games": None, "modified": None, "size_kb": None, "compatible": True,
                       "default": _default_id == RANDOM})
    return {"default": _default_id, "models": models}


def _path_for(model_id: str) -> Optional[Path]:
    if model_id == RANDOM:
        return None
    if model_id == _default_id:
        return _default_path
    try:
        return resolve_checkpoint(model_id)
    except ValueError as exc:
        raise UnknownModel(str(exc)) from None


def get_policy(model_id: Optional[str] = None) -> Tuple[str, GreedyPolicy]:
    """Return (id, policy) for a model id; None means the server default.

    Raises UnknownModel for ids that aren't a checkpoint under models/.
    """
    model_id = model_id or _default_id
    with _lock:
        path = _path_for(model_id)
        if path is not None and model_id != _default_id:
            model_id = _id_for(path)  # canonical id, e.g. "runs/../model.pth" -> "model.pth"
        # best.pth is overwritten during training: a new mtime means new weights.
        key = (model_id, path.stat().st_mtime if path is not None and path.is_file() else None)
        policy = _policies.get(key)
        if policy is not None:
            _policies.move_to_end(key)
            return model_id, policy
        policy = GreedyPolicy(num_actions=num_actions(), model_path=path)
        if policy.is_trained:
            inside = MODELS_DIR.resolve() in Path(path).resolve().parents
            policy.model_name = label_for(describe_checkpoint(path)) if inside else Path(path).name
        _policies[key] = policy
        while len(_policies) > CACHE_SIZE:
            _policies.popitem(last=False)
        return model_id, policy
