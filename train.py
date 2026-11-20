"""Entry point: train the Stone Age DQN agent via self-play.

Usage:
    python train.py                                   # fresh network
    python train.py --resume runs/<run>/games_0010000.pth   # continue a run
    python train.py --list-models                     # every saved model, grouped by run
    tensorboard --logdir models/runs                  # live graphs (http://localhost:6006)
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from stoneage_ai.paths import MODELS_DIR  # noqa: E402


def list_models() -> None:
    """Print every checkpoint in models/, grouped by run, with the stats logged when it was saved."""
    from stoneage_ai.agent.tracking import _fmt, read_checkpoint_log
    from stoneage_ai.checkpoints import list_checkpoints

    checkpoints = list_checkpoints()
    if not checkpoints:
        print(f"No models found in {MODELS_DIR}")
        return
    w = max(len("checkpoint"), *(len(c["path"].name) for c in checkpoints))
    header = (f"  {'checkpoint':<{w}} {'kind':<9} {'games':>9} {'VP':>6} {'cards':>6} "
              f"{'build':>6} {'tools':>6} {'people':>6} {'wheat':>6} {'rounds':>6} {'size':>8}")
    current = object()
    stats = {}
    for c in checkpoints:
        if c["run"] != current:
            current = c["run"]
            title = f"runs/{current}" if current else "models/ (legacy, before run folders)"
            print(f"\n{title}")
            print(header)
            stats = ({row["checkpoint"]: row for row in read_checkpoint_log(MODELS_DIR / "runs" / current)}
                     if current else {})
        row = stats.get(c["path"].name, {})
        games = f"{c['games']:,}" if c["games"] is not None else "?"
        name = c["path"].name
        vp = row.get("vp", row.get("learner_vp"))  # older checkpoints.csv files used learner_vp
        cols = " ".join(f"{_fmt(row.get(k), '.1f'):>6}"
                        for k in ("cards", "buildings", "tools", "people", "wheat", "rounds"))
        print(f"  {name:<{w}} {c['kind']:<9} {games:>9} {_fmt(vp, '.1f'):>6} {cols} "
              f"{c['size_kb']:>5} KB")
    print("\nLearner averages over the last games before each save (from the run's checkpoints.csv).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train the Stone Age DQN agent by self-play.")
    parser.add_argument("--resume", help="checkpoint in models/ (or a path) to continue from")
    parser.add_argument("--no-tensorboard", action="store_true",
                        help="skip TensorBoard; only print the console summary")
    parser.add_argument("--list-models", action="store_true",
                        help="list all saved models (grouped by run) with their stats, then exit")
    args = parser.parse_args()

    if args.list_models:
        list_models()
        sys.exit()

    from stoneage_ai.agent.agent import train  # imported here so --list-models skips torch

    resume = None
    if args.resume:
        resume = Path(args.resume) if Path(args.resume).exists() else MODELS_DIR / args.resume
    train(resume=resume, tensorboard=not args.no_tensorboard)
