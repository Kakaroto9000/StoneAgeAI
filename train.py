"""Entry point: train the Stone Age DQN agent via self-play.

Usage:
    python train.py                                   # fresh network
    python train.py --resume runs/<run>/games_0010000.pth   # continue a run
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from stoneage_ai.agent.agent import train  # noqa: E402
from stoneage_ai.paths import MODELS_DIR  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train the Stone Age DQN agent by self-play.")
    parser.add_argument("--resume", help="checkpoint in models/ (or a path) to continue from")
    args = parser.parse_args()

    resume = None
    if args.resume:
        resume = Path(args.resume) if Path(args.resume).exists() else MODELS_DIR / args.resume
    train(resume=resume)
