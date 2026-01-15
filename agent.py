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
import numpy as np
from game import Game
from collections import deque

# Configuration constants for training
MAX_MEMORY = 100000  # Maximum size of experience replay buffer
BATCH_SIZE = 1000    # Number of experiences sampled per training batch
LR = 0.001          # Learning rate for the neural network optimizer


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
    
    def __init__(self):
        """
        Initialize the agent with empty memory and default RL parameters.
        
        Sets up the experience replay buffer (memory) and initializes game counter.
        Note: Model and trainer should be initialized separately before training.
        """
        self.n_games = 0  # Counter for number of games played
        self.epsilon = 0  # Exploration rate (randomness) - starts at 0, increases with games
        self.gamma = 0    # Discount factor for future rewards - TODO: set to appropriate value (e.g., 0.9)
        
        # Experience replay buffer: stores transitions (s, a, r, s', done)
        # When full, oldest experiences are automatically removed
        self.memory = deque(maxlen=MAX_MEMORY)
        
        self.model = None      # TODO: Initialize neural network model (e.g., DQN network)
        self.trainer = None    # TODO: Initialize trainer class for optimization

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

    def remember(self, state: np.ndarray, action: int, reward: float, 
                 next_state: np.ndarray, done: bool) -> None:
        """
        Store an experience in the replay memory buffer.
        
        This experience will later be sampled during training. When memory
        reaches MAX_MEMORY, the oldest experience is automatically removed.
        
        Args:
            state (np.ndarray): The state before taking the action.
            action (int): The action taken (0-7 for 8 possible moves).
            reward (float): The reward received for this action.
            next_state (np.ndarray): The resulting state after the action.
            done (bool): Whether the game ended after this action.
        """
        self.memory.append((state, action, reward, next_state, done))

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

        # Unpack the batch into separate tuples for each component
        states, actions, rewards, next_states, dones = zip(*mini_sample)
        
        # Pass batch to trainer for one training step
        self.trainer.train_step(states, actions, rewards, next_states, dones)

    def train_short_memory(self, state: np.ndarray, action: int, reward: float,
                          next_state: np.ndarray, done: bool) -> None:
        """
        Train the model immediately on a single experience (short-term learning).
        
        This trains the model right after each action, providing immediate feedback.
        Useful for quick adaptation but should be combined with long-term memory
        training for stability.
        
        Args:
            state (np.ndarray): The state before the action.
            action (int): The action taken.
            reward (float): The reward for the action.
            next_state (np.ndarray): The resulting state.
            done (bool): Whether the game ended.
        """
        self.trainer.train_step(state, action, reward, next_state, done)

    def get_action(self, state: np.ndarray, game: Game) -> np.ndarray:
        """
        Choose an action based on epsilon-greedy exploration strategy.
        
        With probability epsilon, choose a random action (exploration).
        Otherwise, use the neural network to predict the best action (exploitation).
        Epsilon decreases over time, shifting from exploration to exploitation.
        
        Args:
            state (np.ndarray): The current game state.
            game (Game): The game instance (for random valid moves).
        
        Returns:
            np.ndarray: The action vector (size 8 for 8 possible moves).
        """
        # Decrease epsilon over games - more exploration early, more exploitation later
        self.epsilon = 80 - self.n_games
        
        # Initialize action vector (8 possible actions/locations)
        final_move = [0, 0, 0, 0, 0, 0, 0, 0]
        
        # Epsilon-greedy: explore with probability epsilon/200
        if random.randint(0, 200) < self.epsilon:
            # Exploration: pick random valid move
            final_move = game.get_random_valid_move()
        else:
            # Exploitation: use network to predict best move
            state0 = torch.tensor(state, dtype=torch.float)
            prediction = self.model.predict(state0)
            # TODO: Convert prediction to final_move (argmax or similar)
        
        return final_move


def train() -> None:
    """
    Main training loop for the RL agent.
    
    Runs the game repeatedly, collecting experience and training the agent.
    Tracks performance metrics (scores, records) over multiple games.
    
    The training loop:
    1. Gets current game state
    2. Agent chooses action (epsilon-greedy)
    3. Executes action and gets reward and new state
    4. Trains short-term memory immediately
    5. Stores experience in long-term memory
    6. When game ends, trains long-term memory on batch
    7. Resets game and repeats
    
    Note: Some method names in the Game class may have typos and should be verified.
    """
    # Lists to track performance over games
    plot_scores = []          # Score from each game
    plot_mean_scores = []     # Running average of scores
    total_score = 0           # Cumulative score across all games
    record = 0                # Best score achieved so far
    
    # Initialize agent and game
    agent = Agent()
    game = Game()
    
    # Main training loop
    while True:
        # ===== Get old state and choose action =====
        state_old = agent.get_state(game)
        final_move = agent.get_action(state_old, game)

        # ===== Execute action and get feedback =====
        reward, done, score = game.play_ster(final_move)  # Note: check method name "play_ster"
        state_new = agent.get_state(game)

        # ===== Short-term training (immediate feedback) =====
        agent.train_short_memory(state_old, final_move, reward, state_new, done)

        # ===== Store in long-term memory =====
        agent.remember(state_old, final_move, reward, state_new, done)

        # ===== If game ended, train long-term and reset =====
        if done:
            # Train on batch from memory
            game.reset()
            agent.n_games += 1
            agent.train_long_memory(state_old, final_move, reward, state_new, done)
            
            # Track record score
            if score > record:
                record = score
                # TODO: Uncomment when model saving is implemented
                # agent.model.save()

            # Print progress
            print(f'Game {agent.n_games}, Score {score}, Record {record}')


if __name__ == '__main__':
    # Run the training loop when script is executed directly
    train()