
# StoneAgeAI rules

stone_age_rules.pdf
A reinforcement learning agent that learns to play the Stone Age board game through self-play using Deep Q-Networks (DQN).

## Run training

python agent.py

## Structure

python agent.py --play
Project Structure
stone_age/
├── agent.py         # DQN agent + training loop
├── model.py         # Model
├── action_system.py # Module for creating a mask for AI
├── game.py          # Game orchestration + state extraction
├── player.py        # Player state + decisions
├── area.py          # Board locations (base class) and gathering locations
├── building.py      # Purchasable buildings
├── card.py          # Purchasable cards
├── decks.py         # Decks of cards and buildings
└── utility.py       # Special locations (farm, house, tool shop)

## Architecture

Agent -> Game -> Agent -> Model -> Agent-> repeat

## How It Works

1. Game State → Neural Network Input
       The game state is flattened into a 154-element vector and passes it to an agent.
2. Action Space
       The agent chooses an action using his mask
3. Game action
**Reward is changing all the time to improve AI. Check bottom of game.py class for more details**
       Execute of an action and returning a reward
4. Agent
       Learn from an action and reward
5. Repeat if the game isn`t finished yet

## Key Classes

Game
game = Game()                    # Initialize 4-player game
actions = game.get_available_actions()  # Legal moves
reward, done, action_index = game.play_step(action)  # Execute action and sometimes I force it to place a human on a building/card if it has enough resources
game.reset()                     # New game
Agent
state = agent.get_state(game)              # Extract state
action = agent.get_action(state)           # Choose action (ε-greedy)
agent.remember(state, action, reward, next_state, done)
agent.train_short_memory(...)              # Train on single experience
agent.train_long_memory()                  # Train on batch from replay buffer
Player
player.resources      # {2: food, 3: wood, 4: stone, 5: clay, 6: gold}
player.tools          # [[value, available], ...] × 4 slots
player.one_use_tools  # [value, ...] consumable tools
player.multipliers    # {'tools': 0, 'buildings': 0, 'workers': 0, 'wheat': 0}
player.get_vp()       # Calculate total VP including multipliers
player.feed()         # Feed workers at round end
