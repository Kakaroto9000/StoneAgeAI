"""
Inference-only policy for playing with a trained Q-network.

Unlike ``Agent``, this has no replay memory, optimizer or exploration: it
loads a checkpoint once and always picks the highest-valued legal action.
Used by the web UI to drive the AI seats.
"""

from pathlib import Path
from typing import Optional

import numpy as np
import torch

from stoneage_ai.game.game import Game
from stoneage_ai.paths import MODELS_DIR

from .model import Linear_QNet, device

STATE_SIZE = 154
DEFAULT_MODEL = MODELS_DIR / "model.pth"


class GreedyPolicy:
    """Pick the legal action with the highest predicted Q-value.

    Falls back to uniformly random legal moves if no checkpoint is found
    or the checkpoint does not match the current network shape.
    """

    def __init__(self, num_actions: int, model_path: Optional[Path] = DEFAULT_MODEL) -> None:
        self.model: Optional[Linear_QNet] = None
        self.model_name = "random"
        # Why a requested checkpoint could not be used (None if it loaded, or none was asked for).
        self.load_error: Optional[str] = None

        if model_path is not None and not Path(model_path).exists():
            self.load_error = f"no checkpoint at {Path(model_path).name}"
            self.model_name = f"random ({self.load_error})"
            print(f"No checkpoint at {model_path}; AI will play random legal moves.")
        elif model_path is not None:
            model = Linear_QNet(STATE_SIZE, 512, num_actions)
            try:
                model.load_state_dict(torch.load(model_path, map_location=device))
            except RuntimeError:  # shape mismatch with an old checkpoint
                self.load_error = f"{Path(model_path).name} doesn't match the current network"
                self.model_name = f"random ({self.load_error})"
                print(f"{Path(model_path).name} doesn't match the current network "
                      f"(state size {STATE_SIZE}); AI will play random legal moves.")
            else:
                model.eval()
                self.model = model
                self.model_name = Path(model_path).name

    @staticmethod
    def is_compatible(model_path: Path, num_actions: int) -> bool:
        """True if the checkpoint's tensor shapes match the current network."""
        try:
            saved = torch.load(model_path, map_location="cpu")
        except Exception:
            return False
        expected = Linear_QNet(STATE_SIZE, 512, num_actions).state_dict()
        return (isinstance(saved, dict) and saved.keys() == expected.keys()
                and all(tuple(saved[k].shape) == tuple(v.shape) for k, v in expected.items()))

    @property
    def is_trained(self) -> bool:
        return self.model is not None

    def choose(self, game: Game) -> int:
        """Return an action index that is legal in the current game state."""
        mask = game.get_mask().astype(bool)
        legal = np.flatnonzero(mask)
        if len(legal) == 0:
            raise ValueError("No legal actions available")

        if self.model is None:
            return int(np.random.choice(legal))

        with torch.no_grad():
            state = torch.tensor(game.get_state(), dtype=torch.float, device=device)
            q_values = self.model(state)
            q_values[~torch.tensor(mask, device=device)] = float("-inf")
            return int(torch.argmax(q_values).item())
