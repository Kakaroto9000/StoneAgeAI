"""
Agent module for Stone Age reinforcement learning.

This module implements a DQN (Deep Q-Network) based agent that learns to play
the Stone Age board game through self-play and training. The agent stores
experience in memory and trains on batches to improve its decision-making.

Classes:
    Agent: The RL agent that interacts with the game environment.
"""

import torch
import random
from datetime import datetime
import numpy as np
from stoneage_ai.game.game import Game
from collections import deque
from .model import Linear_QNet, QTrainer
from . import rewards

# Configuration constants for training
MAX_MEMORY = 1000000  # Maximum size of experience replay buffer
BATCH_SIZE = 512    # Number of experiences sampled per training batch
LR = 0.001          # Learning rate for the neural network optimizer
CHECKPOINT_EVERY = 10_000  # Save a snapshot to models/runs/<run>/ every N games
LEARNER_SEAT = 0           # Only this seat's (Player 1's) experience is trained on
STATS_WINDOW = 1000        # Games used for the rolling win rate
GAMMA = 0.995              # Discount per learner decision (~150/game): end result keeps ~47% at game start
N_STEP = 16                # Rewards summed per transition before bootstrapping
TARGET_SYNC_GAMES = 20     # Copy the online network into the target network every N games
EPS_START = 0.50           # Chance of a random move at the start of training
EPS_END = 0.05             # ...falling linearly to this
EPS_DECAY_GAMES = 50_000   # ...over this many games, then staying there
RANDOM_SEATS = {3}         # Player 4 always plays uniformly random legal moves


class Agent:
    """
    A reinforcement learning agent for the Stone Age board game.
    
    This agent uses a Deep Q-Network (DQN) approach with experience replay
    to learn optimal strategies through self-play. It maintains a memory of
    past experiences and trains on batches to update its neural network.
    
    Attributes:
        n_games (int): Total number of games played so far.
        epsilon (float): Exploration rate (randomness). Decreases over time
                        to shift from exploration to exploitation.
        gamma (float): Discount factor for future rewards (0-1).
                      Controls how much future rewards matter.
        memory (deque): Experience replay buffer storing (state, action, reward,
                       next_state, done) tuples. Limited to MAX_MEMORY size.
        model: Neural network model for Q-value prediction (to be implemented).
        trainer: Training utility class for updating the model (to be implemented).
    """
    
    def __init__(self, num_actions, model_path=None):
        """
        Initialize the agent with empty memory and default RL parameters.
        
        Sets up the experience replay buffer (memory) and initializes game counter.
        Note: Model and trainer should be initialized separately before training.
        """
        self.n_games = 0  # Counter for number of games played
        self.epsilon = 0  # Exploration rate (randomness) - starts at 0, increases with games
        self.gamma = GAMMA  # Discount factor for future rewards
        
        # Experience replay buffer: stores transitions (s, a, r, s', done)
        # When full, oldest experiences are automatically removed
        self.memory = deque(maxlen=MAX_MEMORY)
        
        self.model = Linear_QNet(154, 512, num_actions)
        if model_path is not None:
            self.model.load_state_dict(torch.load(model_path))
            print(f"Resumed from {model_path}")
    
        self.trainer = QTrainer(self.model, lr=LR, gamma=self.gamma)


    def get_state(self, game: Game) -> np.ndarray:
        """
        Extract and return the current game state as a neural network-compatible array.
        
        This method converts the complex game state (player resources, tools, board
        occupancy, etc.) into a fixed-size numpy array suitable for the DQN network.
        The game.get_state() method handles the actual flattening logic.
        
        Args:
            game (Game): The current game instance to extract state from.
        
        Returns:
            np.ndarray: A 1D array of floats representing the game state,
                       ready for neural network input.
        """
        return game.get_state()

    def remember(self, transition: tuple) -> None:
        """
        Store an n-step transition in the replay buffer.

        ``transition`` is (state, action, reward, next_state, done, next_mask,
        discount); see ``QTrainer`` for what each field means. When memory
        reaches MAX_MEMORY, the oldest experience is automatically removed.
        """
        self.memory.append(transition)

    def train_long_memory(self) -> None:
        """
        Train the model on a batch of experiences from long-term memory.
        
        Samples a random batch from the experience replay buffer and trains
        the model. This batch learning helps break correlation between sequential
        experiences and stabilizes training (a key DQN feature).
        
        The batch size is controlled by BATCH_SIZE constant.
        """
        # Only train if we have enough experiences
        if len(self.memory) > BATCH_SIZE:
            # Sample a random batch to decorrelate experiences
            mini_sample = random.sample(self.memory, BATCH_SIZE)
        else:
            # If memory is small, use all available experiences
            mini_sample = self.memory

        # Unpack the batch into one tuple per field and run one training step
        self.trainer.train_step(*zip(*mini_sample))

    def train_short_memory(self, transition: tuple) -> None:
        """Train immediately on a single n-step transition (see ``remember``)."""
        self.trainer.train_step(*transition)

    def exploration_rate(self) -> float:
        """Linear epsilon schedule: EPS_START -> EPS_END over EPS_DECAY_GAMES games."""
        progress = min(1.0, self.n_games / EPS_DECAY_GAMES)
        return EPS_START + (EPS_END - EPS_START) * progress

    def get_action(self, state: np.ndarray, game: Game) -> int:
        """
        Epsilon-greedy move choice.

        With probability ``exploration_rate()`` pick a random legal move;
        otherwise pick the legal move with the highest predicted Q-value.

        Args:
            state (np.ndarray): The current game state.
            game (Game): The game instance (for the legal-move mask).

        Returns:
            int: Index of the chosen action.
        """
        from .model import device
        self.epsilon = self.exploration_rate()

        if random.random() < self.epsilon:
            return int(game.mask_generator.get_random_valid_action(game))

        with torch.no_grad():
            state0 = torch.tensor(state, dtype=torch.float).to(device)
            prediction = self.model(state0)
            mask = torch.tensor(game.get_mask(), dtype=torch.bool).to(device)
            prediction[~mask] = float('-inf')
            return int(torch.argmax(prediction).item())


def train(resume=None) -> None:
    """
    Self-play training loop that learns from one seat only.

    Players 1-3 choose moves with the same network (epsilon-greedy); Player 4
    (``RANDOM_SEATS``) always plays random legal moves, and its starvation does
    not end the game. Only the learner seat (``LEARNER_SEAT``, Player 1) is
    trained on; the others are opponents whose experience is discarded.

    Each learner transition is from the learner's point of view:

        (s, a) recorded when the learner decides
        r      = everything that happens to the learner until it decides again
                 (its VP change, starvation, potential-based shaping)
        s'     = the learner's NEXT decision state (never an opponent's)

    Up to N_STEP of these are combined into one n-step transition
    (discounted sum of rewards, then bootstrap from the state N_STEP decisions
    later), so the end-of-game result reaches early moves much faster.
    When the game ends, the remaining steps are flushed with done=True and the
    learner's final-VP reward from ``rewards.terminal_rewards``. See
    ``rewards.py`` for the reward design.

    Args:
        resume: optional checkpoint path to continue from; otherwise the
            network starts from random weights.
    """
    record = -10000                         # learner's best VP so far
    recent_wins = deque(maxlen=STATS_WINDOW)

    game = Game()
    game.starvation_exempt = set(RANDOM_SEATS)  # a random seat starving must not end the game
    game.reset()
    agent = Agent(num_actions=game.action_system.NUM_ACTIONS, model_path=resume)

    # Each training run gets its own checkpoint folder, e.g. models/runs/2026-11-18_21-05-33/
    run_dir = f"runs/{datetime.now():%Y-%m-%d_%H-%M-%S}"
    print(f"Training seat {LEARNER_SEAT + 1}; checkpoints every {CHECKPOINT_EVERY:,} games "
          f"-> models/{run_dir}/")

    # The learner's open decision: {"state", "action", "reward", "phi"} or None
    pending = None
    # Finished one-step transitions waiting to be combined into an n-step one:
    # (state, action, shaped_reward, next_state, done, next_mask)
    window = deque()

    def emit(k):
        """Store/train the n-step transition starting at window[0], covering k steps."""
        state, action = window[0][0], window[0][1]
        ret = sum(agent.gamma ** i * window[i][2] for i in range(k))
        _, _, _, next_state, done, next_mask = window[k - 1]
        transition = (state, action, ret, next_state, done, next_mask, agent.gamma ** k)
        agent.train_short_memory(transition)
        agent.remember(transition)
        window.popleft()

    def close(next_state, next_mask, done, extra_reward=0.0, next_phi=0.0):
        """Turn the open decision into a one-step transition and queue it."""
        nonlocal pending
        if pending is None:
            return
        reward = pending["reward"] + extra_reward + agent.gamma * next_phi - pending["phi"]
        window.append((pending["state"], pending["action"], reward, next_state, done, next_mask))
        pending = None
        if done:  # game over: flush everything with shorter horizons
            while window:
                emit(len(window))
        elif len(window) == N_STEP:
            emit(N_STEP)

    while True:
        seat = game.current_player_idx
        learner_turn = seat == LEARNER_SEAT
        state = agent.get_state(game)

        if learner_turn:
            phi = rewards.potential(game, LEARNER_SEAT)
            mask = np.packbits(game.get_mask().astype(bool))
            close(state, mask, False, next_phi=phi)  # learner decides again: previous step ends

        if seat in RANDOM_SEATS:
            action = int(game.mask_generator.get_random_valid_action(game))
        else:
            action = agent.get_action(state, game)
        vp_before = game.players[LEARNER_SEAT].get_vp()
        _, done, action = game.play_step(action)
        vp_after = game.players[LEARNER_SEAT].get_vp()

        if learner_turn:
            pending = {"state": state, "action": action, "reward": 0.0, "phi": phi}
        if pending is not None:
            # Opponents' moves (and round-end feeding) can change the learner's VP too.
            pending["reward"] += (vp_after - vp_before) / rewards.VP_SCALE

        if done:
            final_state = agent.get_state(game)  # ignored by the target when done=True
            no_moves = np.packbits(np.zeros(game.action_system.NUM_ACTIONS, dtype=bool))
            close(final_state, no_moves, True,
                  extra_reward=rewards.terminal_rewards(game)[LEARNER_SEAT])

            final_vps = rewards.vp_snapshot(game)
            learner_vp = final_vps[LEARNER_SEAT]
            recent_wins.append(learner_vp == max(final_vps))
            for player in game.players:
                cards_owned = len(player.card_effects[0]) + len(player.card_effects[1])
                print(f"player end: food={player.resources[2]}, wheat={player.wheat}, "
                      f"workers={player.total_workers}, vp={player.get_vp()}, "
                      f"buildings={player.building_num}, cards={cards_owned}, "
                      f"tools={sum(t[0] for t in player.tools)}, "
                      f"multipliers={list(player.multipliers.values())}, "
                      f"rounds={game.round}, resources={player.resources}")

            game_rounds = game.round
            game.reset()
            agent.n_games += 1
            agent.train_long_memory()
            if agent.n_games % TARGET_SYNC_GAMES == 0:
                agent.trainer.sync_target()

            if learner_vp > record:
                record = learner_vp
                agent.model.save(file_name=f"{run_dir}/best.pth")
            if agent.n_games % CHECKPOINT_EVERY == 0:
                path = agent.model.save(file_name=f"{run_dir}/games_{agent.n_games:07d}.pth")
                print(f"Saved checkpoint {path}")

            win_rate = sum(recent_wins) / len(recent_wins)
            print(f"Game {agent.n_games}, learner vp {learner_vp}, record {record}, "
                  f"opponents {final_vps[:LEARNER_SEAT] + final_vps[LEARNER_SEAT + 1:]}, "
                  f"win rate (last {len(recent_wins)}) {win_rate:.0%}, "
                  f"rounds {game_rounds}, epsilon {agent.epsilon:.2f}")


if __name__ == '__main__':
    # Run the training loop when script is executed directly
    train()
