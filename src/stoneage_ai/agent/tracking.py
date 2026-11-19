"""
Training progress logging: CSV per game, TensorBoard + console per window.

Training runs thousands of games a minute, so the expensive outputs are
aggregated: every game is buffered and written to ``metrics.csv`` once per
window, and TensorBoard / the console get one averaged data point per window
(``log_every`` games). TensorBoard is optional; without it only the CSV and
console are written.

Files live in the run folder, e.g. ``models/runs/2026-11-18_21-05-33/``:
    metrics.csv                  one row per game
    checkpoints.csv              one row per saved checkpoint, with the recent stats at that point
    events.out.tfevents.*        TensorBoard (view with: tensorboard --logdir models/runs);
                                 the "checkpoints" table is under the Text tab
"""

import csv
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

CSV_FIELDS = ["game", "learner_vp", "p1_vp", "p2_vp", "p3_vp", "p4_vp", "win",
              "rounds", "epsilon", "loss", "transitions"]
_P = 2  # column of p1_vp; seat i is column _P + i

CHECKPOINT_FIELDS = ["checkpoint", "games", "saved_at", "window_games", "learner_vp",
                     "win_rate", "rounds", "epsilon", "loss", "record"]


class TrainingLogger:
    def __init__(self, run_dir: Path, learner_seat: int, random_seats=(), log_every: int = 100,
                 use_tensorboard: bool = True, num_seats: int = 4) -> None:
        self.run_dir = Path(run_dir)
        self.learner_seat = learner_seat
        self.random_seats = [i for i in range(num_seats) if i in set(random_seats) and i != learner_seat]
        self.network_seats = [i for i in range(num_seats)
                              if i != learner_seat and i not in self.random_seats]
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.log_every = log_every

        self._csv_file = open(self.run_dir / "metrics.csv", "a", newline="")
        self._csv = csv.writer(self._csv_file)
        if self._csv_file.tell() == 0:
            self._csv.writerow(CSV_FIELDS)

        self.tb = None
        if use_tensorboard and SummaryWriter is not None:
            self.tb = SummaryWriter(log_dir=str(self.run_dir), flush_secs=30)
        elif use_tensorboard:
            print("TensorBoard not installed (pip install tensorboard); logging to CSV only.")

        self._rows: List[list] = []
        self._losses: List[float] = []
        self._window_start = time.perf_counter()
        # Last ``log_every`` game rows (shared references, no copies) for checkpoint stats.
        self._recent = deque(maxlen=log_every)
        self._checkpoints: List[Dict] = read_checkpoint_log(self.run_dir)

    def add_loss(self, loss: Optional[float]) -> None:
        if loss is not None:
            self._losses.append(loss)

    def log_game(self, game: int, final_vps: List[int], won: bool, rounds: int,
                 epsilon: float, transitions: int, record: int) -> None:
        """Record one finished game; writes everything once per ``log_every`` games."""
        loss = mean(self._losses) if self._losses else float("nan")
        self._losses.clear()
        self._rows.append([game, final_vps[self.learner_seat], *final_vps, int(won), rounds,
                           round(epsilon, 4), round(loss, 6), transitions])
        self._recent.append(self._rows[-1])
        if len(self._rows) >= self.log_every:
            self._flush_window(record)

    def _flush_window(self, record: int) -> None:
        rows, self._rows = self._rows, []
        self._csv.writerows(rows)
        self._csv_file.flush()

        game = rows[-1][0]
        elapsed = time.perf_counter() - self._window_start
        self._window_start = time.perf_counter()
        win, rounds, eps, loss = (CSV_FIELDS.index(f) for f in ("win", "rounds", "epsilon", "loss"))
        losses = [r[loss] for r in rows if r[loss] == r[loss]]  # drop NaN

        def seat_mean(seats):
            values = [r[_P + i] for r in rows for i in seats]
            return mean(values) if values else float("nan")

        stats = {
            "vp/learner": mean(r[1] for r in rows),
            "vp/network_opponents": seat_mean(self.network_seats),
            "vp/random_opponent": seat_mean(self.random_seats),
            "win_rate": mean(r[win] for r in rows),
            "rounds": mean(r[rounds] for r in rows),
            "epsilon": rows[-1][eps],
            "loss": mean(losses) if losses else float("nan"),
            "games_per_sec": len(rows) / elapsed if elapsed > 0 else 0.0,
        }

        if self.tb is not None:
            for name, value in stats.items():
                self.tb.add_scalar(name, value, game)
            self.tb.add_scalar("vp/record", record, game)

        print(f"Games {game - len(rows) + 1}-{game} | learner vp {stats['vp/learner']:.1f} "
              f"(record {record}) | net opp {stats['vp/network_opponents']:.1f} | "
              f"random opp {stats['vp/random_opponent']:.1f} | win {stats['win_rate']:.0%} | "
              f"rounds {stats['rounds']:.1f} | eps {stats['epsilon']:.2f} | "
              f"loss {stats['loss']:.4f} | {stats['games_per_sec']:.0f} games/s")

    def recent_stats(self) -> Dict:
        """Averages over the last ``log_every`` games (fewer if the run is younger)."""
        rows = list(self._recent)
        if not rows:
            return {"window_games": 0, "learner_vp": float("nan"), "win_rate": float("nan"),
                    "rounds": float("nan"), "epsilon": float("nan"), "loss": float("nan")}
        win, rounds, eps, loss = (CSV_FIELDS.index(f) for f in ("win", "rounds", "epsilon", "loss"))
        losses = [r[loss] for r in rows if r[loss] == r[loss]]  # drop NaN
        return {
            "window_games": len(rows),
            "learner_vp": round(mean(r[1] for r in rows), 2),
            "win_rate": round(mean(r[win] for r in rows), 3),
            "rounds": round(mean(r[rounds] for r in rows), 2),
            "epsilon": rows[-1][eps],
            "loss": round(mean(losses), 6) if losses else float("nan"),
        }

    def log_checkpoint(self, path, game: int, record: int) -> None:
        """Record a saved checkpoint (periodic or stopped) with the agent's recent stats.

        Appends to ``checkpoints.csv``, refreshes the TensorBoard "checkpoints" text table
        and prints one console line. Only called on checkpoint saves, so cost doesn't matter.
        """
        path = Path(path)
        entry = {"checkpoint": path.name, "games": game,
                 "saved_at": datetime.now().isoformat(timespec="seconds"),
                 **self.recent_stats(), "record": record}
        log_file = self.run_dir / "checkpoints.csv"
        new_file = not log_file.exists() or log_file.stat().st_size == 0
        with open(log_file, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CHECKPOINT_FIELDS)
            if new_file:
                writer.writeheader()
            writer.writerow(entry)
        self._checkpoints.append(entry)

        if self.tb is not None:
            self.tb.add_text("checkpoints", checkpoints_markdown(self._checkpoints), game)
            self.tb.flush()

        print(f"Checkpoint {path.name} after {game:,} games | last {entry['window_games']} games: "
              f"learner vp {_fmt(entry['learner_vp'], '.1f')} | win {_fmt(entry['win_rate'], '.0%')} | "
              f"rounds {_fmt(entry['rounds'], '.1f')} | eps {_fmt(entry['epsilon'], '.2f')} | "
              f"record {record}")

    def close(self, record: int) -> None:
        if self._rows:
            self._flush_window(record)
        self._csv_file.close()
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
    lines = ["| checkpoint | games | saved at | learner VP | win rate | rounds | epsilon | record |",
             "|---|---:|---|---:|---:|---:|---:|---:|"]
    for e in entries:
        lines.append(f"| {e['checkpoint']} | {int(e['games']):,} | {e['saved_at']} | "
                     f"{_fmt(e['learner_vp'], '.2f')} | {_fmt(e['win_rate'], '.1%')} | "
                     f"{_fmt(e['rounds'], '.1f')} | {_fmt(e['epsilon'], '.3f')} | {e['record']} |")
    return "\n".join(lines)
