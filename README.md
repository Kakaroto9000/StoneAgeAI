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
- **Reward function:** Sparse reward based on win/loss outcome, with small intermediate signals for resource efficiency
- **Training loop:** Agent plays against frozen copies of itself, with the opponent updated periodically

### Training Details
| Parameter | Value |
|---|---|
| Training matches | 200,000+ |
| Optimizer | Adam |
| Discount factor (γ) | 0.99 |
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
│   └── agent/                # RL agent
│       ├── agent.py          # DQN agent and self-play training loop
│       └── model.py          # Q-network and trainer
├── models/                   # Saved model checkpoints (.pth)
├── docs/stone_age_rules.pdf  # Official game rules
├── train.py                  # Entry point for training
├── requirements.txt
└── pyproject.toml
```

---

## Getting Started

```bash
git clone https://github.com/Kakaroto9000/StoneAgeAI.git
cd StoneAgeAI
pip install -r requirements.txt

# Train the agent
python train.py
```

---

## Author

**Oleksandr (Sasha) Klindukh**
Northeastern University — Computer Science
[klindukh.o@northeastern.edu](mailto:klindukh.o@northeastern.edu)
