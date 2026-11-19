"""
FastAPI app: play Stone Age in the browser against the trained agent.

Endpoints:
    POST /api/games                  start a game (human seat or spectate)
    GET  /api/games/{id}             current state
    POST /api/games/{id}/move        submit the human's action, then AI plays
    POST /api/games/{id}/advance     let AI seats play (spectator mode / catch-up)

Run with ``python play.py`` from the repo root.
"""

from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from stoneage_ai.agent.policy import DEFAULT_MODEL, GreedyPolicy
from stoneage_ai.game.game import Game

from .session import GameSession, IllegalMove

STATIC_DIR = Path(__file__).resolve().parent / "static"
MAX_SESSIONS = 200

app = FastAPI(title="Stone Age AI")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# One shared policy: the network is loaded lazily, once, for inference only.
_policy: Optional[GreedyPolicy] = None
_model_path: Optional[Path] = DEFAULT_MODEL
_sessions: Dict[str, GameSession] = {}


def configure(model_path: Optional[Path]) -> None:
    """Choose the checkpoint AI seats use (None = random moves). Call before serving."""
    global _model_path, _policy
    _model_path, _policy = model_path, None


def get_policy() -> GreedyPolicy:
    global _policy
    if _policy is None:
        probe = Game()
        probe.reset()
        _policy = GreedyPolicy(num_actions=probe.action_system.NUM_ACTIONS, model_path=_model_path)
    return _policy


def get_session(game_id: str) -> GameSession:
    session = _sessions.get(game_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return session


class NewGame(BaseModel):
    human_seat: Optional[int] = Field(0, ge=0, le=3, description="null to spectate")


class Move(BaseModel):
    action_index: int = Field(..., ge=0)


class Advance(BaseModel):
    max_steps: int = Field(1, ge=1, le=5000)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/games")
def new_game(body: NewGame) -> dict:
    if len(_sessions) >= MAX_SESSIONS:  # drop the oldest game
        _sessions.pop(next(iter(_sessions)))
    session = GameSession(get_policy(), human_seat=body.human_seat)
    _sessions[session.id] = session
    with session.lock:
        if session.human_seat is not None:
            session.advance_ai()  # AI seats before the human play first
        return session.to_dict()


@app.get("/api/games/{game_id}")
def get_game(game_id: str) -> dict:
    session = get_session(game_id)
    with session.lock:
        return session.to_dict()


@app.post("/api/games/{game_id}/move")
def move(game_id: str, body: Move) -> dict:
    session = get_session(game_id)
    with session.lock:
        if body.action_index >= session.game.action_system.NUM_ACTIONS:
            raise HTTPException(status_code=400, detail="Unknown action")
        try:
            session.human_move(body.action_index)
        except IllegalMove as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        session.advance_ai()
        return session.to_dict()


@app.post("/api/games/{game_id}/advance")
def advance(game_id: str, body: Advance) -> dict:
    session = get_session(game_id)
    with session.lock:
        session.advance_ai(max_steps=body.max_steps)
        return session.to_dict()
