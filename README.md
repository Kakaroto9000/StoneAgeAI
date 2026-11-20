# Stone Age AI 

A reinforcement learning agent trained to play the [Stone Age](https://boardgamegeek.com/boardgame/34635/stone-age) board game — built from scratch in Python using Deep Q-Networks (DQN) and PyTorch.

---

## Overview

This project has two major components:

1. **Game Engine** — A full implementation of the Stone Age board game in Python, including all game rules, player actions, resource management, and win conditions.
2. **RL Agent** — A Deep Q-Network agent that learns to play the game by competing against copies of itself across 200,000+ matches.

The agent was given no hand-crafted strategy or heuristics — all behavior emerges purely from self-play and reward signals.

---

## Tech Stack

- **Language:** Python
- **ML Framework:** PyTorch
- **Architecture:** Deep Q-Network (DQN)
- **Training:** Self-play (agent vs. copies of itself)

---

## How It Works

### Game Engine
The board game was implemented as a state machine where each turn consists of:
- Placing workers on resource/action spaces
- Collecting resources based on dice rolls
- Purchasing buildings or civilization cards
- Managing population and tool upgrades

All game logic is encapsulated and exposes a clean API for the RL agent to interact with.

### RL Agent
The agent uses a Deep Q-Network to approximate the action-value function Q(s, a):

- **State representation:** Encoded game state vector (resources, workers, scores, board occupancy)
- **Action space:** All legal moves available on a given turn
- **Reward function** (see `src/stoneage_ai/agent/rewards.py`):
  - each seat gets its own change in VP (÷20), so starvation's −10 VP counts once, when it happens. Starving doesn't end the game.
  - food hoarding penalty: at each round's feeding, every food above 20 still held costs 0.25 VP-equivalent (`FOOD_LIMIT` / `FOOD_PENALTY_VP`)
  - potential-based shaping for holding building resources (doesn't change the optimal policy)
  - at game end, final VP on a scale up to 200 VP: 0 → −1, 10 → −0.8, 20 → −0.5, 40 → −0.2, 70 → 0, 100 → +0.3, 150 → +0.7, 200+ → +1, linear in between (`FINAL_VP_SCALE` in `rewards.py`)
- **Training loop:** one network plays all four seats, but only Player 1 (the learner seat) is trained on — its actions, the rewards it receives, and its final result. The other three seats are opponents whose experience is discarded. The next state in each transition is always Player 1's next decision, never an opponent's

### Training Details
| Parameter | Value |
|---|---|
| Training matches | 200,000+ |
| Optimizer | Adam |
| Discount factor (γ) | 0.995 per Player 1 decision |
| Returns | 16-step (rewards summed over 16 decisions before bootstrapping) |
| Target | Double DQN with a target network synced every 20 games, max over legal moves only |
| Exploration | ε-greedy with decay |
| Replay buffer | Experience replay |

---

## Results

After training, the agent consistently outperforms a random baseline and demonstrates recognizable strategic behavior including resource prioritization, tool investment timing, and worker placement competition.

---

## Project Structure

```
StoneAgeAI/
├── src/stoneage_ai/
│   ├── paths.py              # Repo-relative paths (models/ directory)
│   ├── game/                 # Game engine
│   │   ├── game.py           # Game state machine and turn loop
│   │   ├── player.py         # Player state and actions
│   │   ├── area.py           # Area base class and gathering spaces
│   │   ├── utility.py        # Farm, hut, tool-maker spaces
│   │   ├── card.py           # Civilization cards
│   │   ├── building.py       # Building tiles
│   │   ├── decks.py          # Card and building deck definitions
│   │   └── action_system.py  # Action encoding and legal-move masks
│   ├── agent/                # RL agent
│   │   ├── agent.py          # DQN agent and self-play training loop
│   │   ├── model.py          # Q-network and trainer
│   │   └── policy.py         # Inference-only greedy policy (used by the UI)
│   └── web/                  # Browser UI
│       ├── server.py         # FastAPI app and JSON API
│       ├── session.py        # One browser game: human seat, AI turns, log
│       ├── serialize.py      # Engine state -> JSON / readable text
│       └── static/           # index.html, app.js, style.css (no build step)
├── models/                   # Saved model checkpoints (.pth)
├── docs/stone_age_rules.pdf  # Official game rules
├── train.py                  # Entry point for training
├── play.py                   # Entry point for the web UI
├── requirements.txt
└── pyproject.toml
```

---

## Getting Started

```bash
git clone https://github.com/Kakaroto9000/StoneAgeAI.git
cd StoneAgeAI
pip install -r requirements.txt

# Train the agent (fresh network; checkpoints every 10,000 games in models/runs/<timestamp>/)
python train.py
python train.py --resume runs/<run>/games_0010000.pth   # continue from a checkpoint
python train.py --no-tensorboard                         # CSV + console only

# Play against the trained agent in the browser (http://127.0.0.1:8000)
python play.py
```

### Tracking training

Tracking follows Player 1, the seat being trained. At the end of every game it records Player 1's **VP**, **resources collected** over the whole game (food, wood, stone, clay, gold), **cards and buildings bought**, **tools** (total value), **people** and **wheat** (fields). It also records training health: rounds played, ε and loss. Each run writes to its own folder, `models/runs/<timestamp>/`:

- **Console:** one line per 100 games with Player 1's averages, the VP record (best single game in those 100), rounds, ε, loss and games/s.
- **TensorBoard:** the same averages as live graphs under `player1/*`, `player1_collected/*` and `training/*`. Run `tensorboard --logdir models/runs` in a second terminal and open http://localhost:6006.
- **Checkpoints:** `games_0010000.pth` every 10k games, `best.pth` whenever Player 1 beats its best VP so far in the run, and `games_<n>_stopped.pth` when you press Ctrl+C.
- **Trained models (`checkpoints.csv`):** one row per periodic or stopped checkpoint with Player 1's averages over the last 100 games at that point. The console prints a `Checkpoint ...` line on each save, and TensorBoard's **Text** tab shows the run's checkpoint table.

If the loss shows `nan`, stop training: the network has broken. `get_state()` now raises an error as soon as a NaN appears in the game state, which is how the last one got in.

To see every trained model across all runs (legacy `models/*.pth` files included, with unknown games):

```bash
python train.py --list-models
```

### Web UI options

```bash
python play.py                              # AI uses your newest checkpoint (random moves if there is none)
python play.py --model runs/2026-11-18_21-05-33/best.pth
python play.py --model random               # AI seats play random legal moves
python play.py --host 0.0.0.0 --port 9000   # serve on your network
```

In the UI you can take any of the four seats or choose **Watch 4 AIs** to see the agent play itself. Legal spaces are highlighted, and the server only accepts moves from the engine's own action mask.

The **Model** picker next to the seat chooses which checkpoint the AI players use for the next game (and for *Play again*): any snapshot from a training run (e.g. "Run 2026-11-18 21:05 · 10,000 games", "… · best", "… · stopped at 250 games"), older files in `models/` (marked *legacy*), or random moves. By default the newest checkpoint is selected; `--model` changes that. Checkpoints that don't fit the current network are labelled *incompatible, plays random*, and the header shows the model actually playing.

API (used by the frontend, handy for scripting):

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/models` | Checkpoints the AI can use (`id`, `label`, `kind`, `games`, `compatible`, `default`) plus `"random"` |
| `POST` | `/api/games` | Start a game: `{"human_seat": 0-3 or null, "model": id or "random"}` (`model` optional, defaults to `--model`) |
| `GET` | `/api/games/{id}` | Current state and your legal actions |
| `POST` | `/api/games/{id}/move` | `{"action_index": n}`, then AI seats play until your turn |
| `POST` | `/api/games/{id}/advance` | `{"max_steps": n}` let AI seats play (spectator mode) |

---

## Author

**Oleksandr (Sasha) Klindukh**
Northeastern University — Computer Science
[klindukh.o@northeastern.edu](mailto:klindukh.o@northeastern.edu)
