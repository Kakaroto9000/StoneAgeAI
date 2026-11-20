"""
Reward design for self-play training.

Every seat is rewarded for its own progress, measured from its own point of view:

1. Step reward: change in the seat's VP since its previous decision, divided by
   VP_SCALE. Starvation (-10 VP) is included automatically.
2. Shaping: potential-based, ``gamma * phi(s') - phi(s)``. Phi values the
   building resources a seat holds, which nudges it toward gathering wood,
   stone, clay and gold without changing which policy is optimal
   (Ng et al., 1999). Phi is 0 at the end of the game.
3. Terminal reward: the seat's final VP mapped onto -1..+1 by FINAL_VP_SCALE,
   straight lines between the points (see ``final_score_reward``):
   0 VP or less -> -1, 10 -> -0.8, 20 -> -0.5, 40 -> -0.2, 70 -> 0,
   100 -> +0.3, 150 -> +0.7, 200 VP or more -> +1. Edit the points as the
   agent improves so the scale keeps telling good games from great ones.

Rewards are kept roughly within -1..+1 per transition so Q-values stay small.
"""

from typing import List

from stoneage_ai.game.game import Game

VP_SCALE = 20.0          # 20 VP == reward of 1.0
SHAPING_WEIGHT = 0.3     # fraction of a resource's building value counted in phi
# (final VP, terminal reward), VP ascending. Below the first point -> its reward,
# above the last -> its reward; linear in between. 200 VP is treated as the maximum.
FINAL_VP_SCALE = [
    (0, -1.0),
    (10, -0.8),
    (20, -0.5),
    (40, -0.2),
    (70, 0.0),
    (100, 0.3),
    (150, 0.7),
    (200, 1.0),
]

# Buildings score the face value of the resources spent: wood 3 ... gold 6.
_BUILDING_RESOURCES = (3, 4, 5, 6)


def vp_snapshot(game: Game) -> List[int]:
    """Total VP of every seat right now."""
    return [p.get_vp() for p in game.players]


def potential(game: Game, seat: int) -> float:
    """phi(s): value of the building resources ``seat`` is holding."""
    resources = game.players[seat].resources
    held_value = sum(r * resources[r] for r in _BUILDING_RESOURCES)
    return SHAPING_WEIGHT * held_value / VP_SCALE


def final_score_reward(vp: float, scale=FINAL_VP_SCALE) -> float:
    """Final VP -> terminal reward, by straight lines between the points of ``scale``."""
    if vp <= scale[0][0]:
        return scale[0][1]
    for (vp_lo, r_lo), (vp_hi, r_hi) in zip(scale, scale[1:]):
        if vp <= vp_hi:
            return r_lo + (r_hi - r_lo) * (vp - vp_lo) / (vp_hi - vp_lo)
    return scale[-1][1]


def terminal_rewards(game: Game) -> List[float]:
    """End-of-game reward for every seat, based on its own final VP."""
    return [final_score_reward(vp) for vp in vp_snapshot(game)]
