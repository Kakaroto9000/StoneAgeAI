"""
FastAPI app: play Stone Age in the browser against the trained agent.

Endpoints:
    GET  /api/models                 checkpoints the AI seats can use, plus "random"
    POST /api/games                  start a game (human seat or spectate, optional model)
    GET  /api/games/{id}             current state
    POST /api/games/{id}/move        submit the human's action, then AI plays
    POST /api/games/{id}/advance     let AI seats play (spectator mode / catch-up)
    GET  /api/training[?run=<name>]  training runs and one run's progress/log
    POST /api/training               start training (new or continue, choose opponents)
    POST /api/training/stop          stop a run after its current game

Run with ``python play.py`` from the repo root.
"""

from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from stoneage_ai.agent.policy import GreedyPolicy
from stoneage_ai.checkpoints import latest_checkpoint, resolve_checkpoint

from . import models, training
from .session import GameSession, IllegalMove

STATIC_DIR = Path(__file__).resolve().parent / "static"
MAX_SESSIONS = 200

app = FastAPI(title="Stone Age AI")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Policies are loaded lazily and cached per model (see web/models.py).
_sessions: Dict[str, GameSession] = {}
models.configure_default(latest_checkpoint())  # newest checkpoint, or random if none


def configure(model_path: Optional[Path]) -> None:
    """Choose the default checkpoint AI seats use (None = random moves). Call before serving."""
    models.configure_default(model_path)


def get_session(game_id: str) -> GameSession:
    session = _sessions.get(game_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return session


class NewGame(BaseModel):
    human_seat: Optional[int] = Field(0, ge=0, le=3, description="null to spectate")
    model: Optional[str] = Field(None, description='checkpoint id from /api/models, or "random"; '
                                                   "omit for the server default")


class Move(BaseModel):
    action_index: int = Field(..., ge=0)


class Advance(BaseModel):
    max_steps: int = Field(1, ge=1, le=5000)


class StartTraining(BaseModel):
    resume: Optional[str] = Field(None, description="checkpoint id to continue from; null = new model")
    opponents: List[str] = Field(["self", "self", "random"], min_length=3, max_length=3,
                                 description='3 of: "self", "random" or a checkpoint id')
    tensorboard: bool = True


class StopTraining(BaseModel):
    run: Optional[str] = None


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/training")
def training_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "training.html")


@app.get("/api/models")
def list_models() -> dict:
    return models.list_models()


@app.post("/api/games")
def new_game(body: NewGame) -> dict:
    try:
        model_id, policy = models.get_policy(body.model)
    except models.UnknownModel as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if len(_sessions) >= MAX_SESSIONS:  # drop the oldest game
        _sessions.pop(next(iter(_sessions)))
    session = GameSession(policy, human_seat=body.human_seat, model_id=model_id)
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


def _usable_checkpoint(checkpoint_id: str) -> Path:
    try:
        path = resolve_checkpoint(checkpoint_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not GreedyPolicy.is_compatible(path, models.num_actions()):
        raise HTTPException(status_code=400,
                            detail=f"{checkpoint_id} doesn't match the current network")
    return path


@app.get("/api/training")
def training_status(run: Optional[str] = None) -> dict:
    try:
        return training.status(run)
    except training.TrainingError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/api/training")
def start_training(body: StartTraining) -> dict:
    resume = _usable_checkpoint(body.resume) if body.resume else None
    opponents = [o if o in ("self", "random") else str(_usable_checkpoint(o)) for o in body.opponents]
    try:
        run = training.start(resume, opponents, tensorboard=body.tensorboard)
    except training.TrainingError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return training.status(run)


@app.post("/api/training/stop")
def stop_training(body: StopTraining) -> dict:
    try:
        run = training.stop(body.run)
    except training.TrainingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return training.status(run)
