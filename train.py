"""Entry point: train the Stone Age DQN agent via self-play.

Usage:
    python train.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from stoneage_ai.agent.agent import train  # noqa: E402

if __name__ == "__main__":
    train()
