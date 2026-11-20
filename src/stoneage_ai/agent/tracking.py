"""
Training progress logging focused on the learner (the seat being trained, which rotates every game).

What is tracked, per game, for the learner at the end of the game:
    vp                                   final victory points
    food, wood, stone, clay, gold        resources collected over the whole game
    cards, buildings                     civilization cards / buildings bought
    tools, people, wheat                 total tool value, people, fields (wheat)
plus training health: rounds played, epsilon, loss, transitions stored.

Training runs many games a second, so nothing is written per game: games are
kept in memory and TensorBoard / the console get one averaged data point per
window (``log_every`` games). TensorBoard is optional; without it only the
console line is printed.

Files live in the run folder, e.g. ``models/runs/2026-11-18_21-05-33/``:
    checkpoints.csv              one row per saved checkpoint, with the recent averages at that point
    progress.jsonl               one JSON line per window (the averages; read by the web UI)
    events.out.tfevents.*        TensorBoard (view with: tensorboard --logdir models/runs);
                                 the "checkpoints" table is under the Text tab
"""

import csv
import json
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Dict, List, Optional

try:
    from torch.utils.tensorboard import SummaryWriter
except ImportError:  # tensorboard not installed
    SummaryWriter = None

RESOURCE_FIELDS = ["food", "wood", "stone", "clay", "gold"]
PLAYER_FIELDS = ["vp", *RESOURCE_FIELDS, "cards", "buildings", "tools", "people", "wheat"]
TRAINING_FIELDS = ["rounds", "epsilon", "loss", "transitions"]

CHECKPOINT_FIELDS = ["checkpoint", "games", "saved_at", "window_games", *PLAYER_FIELDS,
                     "vp_record", "rounds", "epsilon", "loss"]


def player_summary(player) -> Dict[str, int]:
    """The learner's end-of-game stats. Call before ``game.reset()``."""
    return {
        "vp": player.get_vp(),
        **{name: player.collected[key] for key, name in zip((2, 3, 4, 5, 6), RESOURCE_FIELDS)},
        "cards": player.cards_bought,
        "buildings": player.building_num,
        "tools": sum(t[0] for t in player.tools),
        "people": player.total_workers,
        "wheat": player.wheat,
    }


def _nanmean(values) -> float:
    values = [v for v in values if v == v]  # drop NaN
    return mean(values) if values else float("nan")


class TrainingLogger:
    def __init__(self, run_dir: Path, log_every: int = 100, use_tensorboard: bool = True,
                 player_label: str = "learner") -> None:
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.log_every = log_every
        self.label = player_label

        self.tb = None
        if use_tensorboard and SummaryWriter is not None:
            self.tb = SummaryWriter(log_dir=str(self.run_dir), flush_secs=30)
        elif use_tensorboard:
            print("TensorBoard not installed (pip install tensorboard); logging to CSV only.")

        self._rows: List[Dict] = []
        self._losses: List[float] = []
        self._window_start = time.perf_counter()
        # Last ``log_every`` game rows (shared references, no copies) for checkpoint stats.
        self._recent = deque(maxlen=log_every)
        self._checkpoints: List[Dict] = read_checkpoint_log(self.run_dir)

    def add_loss(self, loss: Optional[float]) -> None:
        if loss is not None:
            self._losses.append(loss)

    def log_game(self, game: int, player_stats: Dict[str, int], rounds: int,
                 epsilon: float, transitions: int) -> None:
        """Record one finished game; reports averages once per ``log_every`` games.

        ``player_stats`` comes from ``player_summary(learner)`` taken before reset.
        """
        row = {"game": game, **player_stats, "rounds": rounds, "epsilon": round(epsilon, 4),
               "loss": round(_nanmean(self._losses), 6), "transitions": transitions}
        self._losses.clear()
        self._rows.append(row)
        self._recent.append(row)
        if len(self._rows) >= self.log_every:
            self._flush_window()

    @staticmethod
    def _averages(rows: List[Dict]) -> Dict[str, float]:
        stats = {f: mean(r[f] for r in rows) for f in PLAYER_FIELDS + ["rounds"]}
        stats["vp_record"] = max(r["vp"] for r in rows)  # best single game in this window
        stats["epsilon"] = rows[-1]["epsilon"]
        stats["loss"] = _nanmean(r["loss"] for r in rows)
        return stats

    def _flush_window(self, partial: bool = False) -> None:
        rows, self._rows = self._rows, []

        game = rows[-1]["game"]
        elapsed = time.perf_counter() - self._window_start
        self._window_start = time.perf_counter()
        s = self._averages(rows)
        games_per_sec = len(rows) / elapsed if elapsed > 0 else 0.0

        point = {"game": game, "games_per_sec": round(games_per_sec, 3),
                 **{k: (None if v != v else round(v, 4)) for k, v in s.items()}}  # NaN -> null
        if not partial:  # a few leftover games at the end would be a misleading chart point
            with open(self.run_dir / "progress.jsonl", "a") as f:
                f.write(json.dumps(point) + "\n")

        if self.tb is not None:
            p = self.label
            self.tb.add_scalar(f"{p}/vp", s["vp"], game)
            self.tb.add_scalar(f"{p}/vp_record", s["vp_record"], game)
            for f in ("cards", "buildings", "tools", "people", "wheat"):
                self.tb.add_scalar(f"{p}/{f}", s[f], game)
            for f in RESOURCE_FIELDS:
                self.tb.add_scalar(f"{p}_collected/{f}", s[f], game)
            self.tb.add_scalar("training/rounds", s["rounds"], game)
            self.tb.add_scalar("training/epsilon", s["epsilon"], game)
            self.tb.add_scalar("training/loss", s["loss"], game)
            self.tb.add_scalar("training/games_per_sec", games_per_sec, game)

        res = "collected " + " ".join(f"{f} {s[f]:.1f}" for f in RESOURCE_FIELDS)
        print(f"Games {game - len(rows) + 1}-{game} | VP {s['vp']:.1f} (record {s['vp_record']}) | {res} | "
              f"cards {s['cards']:.1f} buildings {s['buildings']:.1f} tools {s['tools']:.1f} "
              f"people {s['people']:.1f} wheat {s['wheat']:.1f} | rounds {s['rounds']:.1f} | "
              f"eps {s['epsilon']:.2f} | loss {s['loss']:.4f} | {games_per_sec:.0f} games/s")

    def recent_stats(self) -> Dict:
        """Averages over the last ``log_every`` games (fewer if the run is younger)."""
        rows = list(self._recent)
        if not rows:
            return {"window_games": 0, **{f: float("nan") for f in CHECKPOINT_FIELDS[4:-1]}}
        stats = {k: round(v, 4) for k, v in self._averages(rows).items()}
        stats["vp_record"] = int(stats["vp_record"])
        return {"window_games": len(rows), **stats}

    def log_checkpoint(self, path, game: int) -> None:
        """Record a saved checkpoint (periodic or stopped) with the learner's recent averages.

        Appends to ``checkpoints.csv``, refreshes the TensorBoard "checkpoints" text table
        and prints one console line. Only called on checkpoint saves, so cost doesn't matter.
        """
        path = Path(path)
        entry = {"checkpoint": path.name, "games": game,
                 "saved_at": datetime.now().isoformat(timespec="seconds"),
                 **self.recent_stats()}
        log_file = self.run_dir / "checkpoints.csv"
        new_file = not log_file.exists() or log_file.stat().st_size == 0
        with open(log_file, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CHECKPOINT_FIELDS, extrasaction="ignore")
            if new_file:
                writer.writeheader()
            writer.writerow(entry)
        self._checkpoints.append(entry)

        if self.tb is not None:
            self.tb.add_text("checkpoints", checkpoints_markdown(self._checkpoints), game)
            self.tb.flush()

        print(f"Checkpoint {path.name} after {game:,} games | last {entry['window_games']} games: "
              f"VP {_fmt(entry['vp'], '.1f')} | cards {_fmt(entry['cards'], '.1f')} | "
              f"buildings {_fmt(entry['buildings'], '.1f')} | tools {_fmt(entry['tools'], '.1f')} | "
              f"people {_fmt(entry['people'], '.1f')} | wheat {_fmt(entry['wheat'], '.1f')} | "
              f"rounds {_fmt(entry['rounds'], '.1f')} | record {_fmt(entry['vp_record'], '.0f')}")

    def close(self) -> None:
        if self._rows:
            self._flush_window(partial=True)
        if self.tb is not None:
            self.tb.close()


def _fmt(value, spec: str) -> str:
    """Format a number, or "-" if it's missing/NaN/not a number (e.g. read back from CSV)."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "-"
    return "-" if value != value else format(value, spec)


def read_checkpoint_log(run_dir: Path) -> List[Dict]:
    """Rows of ``<run_dir>/checkpoints.csv`` as dicts of strings ([] if there is none)."""
    log_file = Path(run_dir) / "checkpoints.csv"
    if not log_file.exists():
        return []
    with open(log_file, newline="") as f:
        return list(csv.DictReader(f))


def checkpoints_markdown(entries: List[Dict]) -> str:
    """Markdown table of checkpoints (for TensorBoard's Text tab)."""
    lines = ["| checkpoint | games | saved at | VP | cards | buildings | tools | people | wheat "
             "| rounds | VP record |",
             "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for e in entries:
        vp = e.get("vp", e.get("learner_vp"))  # older checkpoints.csv files used learner_vp
        lines.append(f"| {e['checkpoint']} | {int(e['games']):,} | {e['saved_at']} | "
                     f"{_fmt(vp, '.1f')} | {_fmt(e.get('cards'), '.1f')} | "
                     f"{_fmt(e.get('buildings'), '.1f')} | {_fmt(e.get('tools'), '.1f')} | "
                     f"{_fmt(e.get('people'), '.1f')} | {_fmt(e.get('wheat'), '.1f')} | "
                     f"{_fmt(e.get('rounds'), '.1f')} | {_fmt(e.get('vp_record', e.get('record')), '.0f')} |")
    return "\n".join(lines)
