"""
A single browser game: one Game, which seat (if any) is human, and an event log.

The engine has one entry point, ``Game.play_step(action_index)``, and a legal
move mask. Humans and AI go through the same path; the only difference is
where the action index comes from.
"""

import threading
import uuid
from typing import Any, Dict, List, Optional

from stoneage_ai.agent.policy import GreedyPolicy
from stoneage_ai.game.game import Game

from . import serialize

MAX_AI_STEPS_PER_CALL = 5000  # safety net against an engine loop


class IllegalMove(Exception):
    pass


class GameSession:
    def __init__(self, policy: GreedyPolicy, human_seat: Optional[int] = 0,
                 model_id: Optional[str] = None) -> None:
        self.id = uuid.uuid4().hex[:12]
        self.policy = policy
        self.model_id = model_id  # which entry of /api/models the AI seats use
        self.human_seat = human_seat
        self.lock = threading.Lock()
        self.game = Game()
        self.game.reset()
        self.log: List[Dict[str, Any]] = []
        self.error: Optional[str] = None

    # ----- turn handling -------------------------------------------------

    @property
    def finished(self) -> bool:
        return self.game.game_end or self.error is not None

    @property
    def waiting_for_human(self) -> bool:
        return (not self.finished and self.human_seat is not None
                and self.game.current_player_idx == self.human_seat)

    def _apply(self, action_index: int) -> None:
        game = self.game
        actor = game.current_player_idx
        round_before = game.round
        text = serialize.describe_action(game, action_index)
        before = {i: dict(p.resources) for i, p in enumerate(game.players)}

        game.play_step(action_index)

        # Gathering text already states the amount; skip diffs that would
        # include end-of-round feeding.
        phase_before_was_gather = text.startswith("rolled ")
        same_round = game.round == round_before
        gained = (serialize.resource_diff(before[actor], game.players[actor].resources)
                  if same_round and not phase_before_was_gather else "")
        self.log.append({
            "round": round_before + 1,
            "player": actor,
            "text": text + (f" ({gained})" if gained else ""),
        })
        if game.round != round_before:
            self.log.append({"round": game.round + 1, "player": None,
                             "text": f"Round {game.round} ended, everyone fed their people"})
        if game.game_end:
            self.log.append({"round": game.round, "player": None, "text": "Game over"})

    def end_reason(self) -> Optional[str]:
        """Why Game.game_ended() fired, in words."""
        game = self.game
        if not game.game_end:
            return None
        starved = [i for i, p in enumerate(game.players) if p.vp < 0]
        if starved:
            who = ", ".join(f"Player {i + 1}" for i in starved)
            return f"Game ends early: {who} couldn't feed their people."
        if game.round >= 25:
            return "Game ends after 25 rounds."
        if not game.cards_in_deck:
            return "Game ends: the civilization deck ran out."
        return "Game ends: a building stack ran out."

    def human_move(self, action_index: int) -> None:
        if not self.waiting_for_human:
            raise IllegalMove("It is not your turn")
        if not self.game.get_mask()[action_index]:
            raise IllegalMove("That move is not legal right now")
        self._apply(action_index)

    def advance_ai(self, max_steps: int = MAX_AI_STEPS_PER_CALL) -> int:
        """Play AI turns until a human must act, the game ends, or max_steps."""
        steps = 0
        while not self.finished and not self.waiting_for_human and steps < max_steps:
            try:
                self._apply(self.policy.choose(self.game))
            except Exception as exc:  # engine bug: stop cleanly instead of hanging
                self.error = f"Engine error: {exc}"
            steps += 1
        return steps

    # ----- view ----------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        game = self.game
        players = [serialize.serialize_player(p, i, i == self.human_seat)
                   for i, p in enumerate(game.players)]
        state: Dict[str, Any] = {
            "id": self.id,
            "round": game.round + 1,
            "human_seat": self.human_seat,
            "current_player": game.current_player_idx,
            "first_player": game.first_player,
            "finished": self.finished,
            "error": self.error,
            "ai_model": self.policy.model_name,
            "ai_model_id": self.model_id,
            "players": players,
            "locations": [serialize.serialize_location(game, loc, i)
                          for i, loc in enumerate(game.locations)],
            "cards_in_deck": len(game.cards_in_deck),
            "decision": serialize.pending_decision(game),
            "legal_actions": serialize.legal_actions(game) if self.waiting_for_human else [],
            "log": self.log[-60:],
        }
        if game.game_end:
            best = max(p["vp"] for p in players)
            state["winners"] = [p["index"] for p in players if p["vp"] == best]
            state["end_reason"] = self.end_reason()
        return state
