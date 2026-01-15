# StoneAgeAI - Stone Age Board Game RL Implementation

A reinforcement learning implementation of the Stone Age board game, where an AI agent learns optimal strategies through self-play and training using Deep Q-Networks (DQN).

## Project Overview

This project implements a complete Stone Age board game simulator with an integrated reinforcement learning agent. The agent uses DQN to learn winning strategies through experience and self-play.

**Status**: Game mechanics partially implemented. Core classes and game flow established. RL agent framework in place with training loop skeleton.

## Game Rules (Stone Age)

Stone Age is a worker placement board game where players develop early civilizations through:

- **Worker Placement**: Players place workers at board locations each round
- **Resource Gathering**: Workers collect food, wood, stone, clay, and gold
- **Building/Cards**: Players purchase buildings and cards for victory points
- **Tools**: Improve resource gathering efficiency
- **Wheat/Wheat Tracking**: Reduce food consumption cost
- **Victory Points**: Won from buildings, cards, and end-game bonuses

## Architecture

### Core Modules

#### `area.py` - Board Locations
Abstract base class for all board locations with concrete implementations:

- **Area**: Base class with capacity tracking and worker placement
  - `place()`: Add workers to location
  - `can_place()`: Check if placement is possible
  - `is_occupied()`: Check if player has workers here
  - `available_space()`: Get remaining capacity

- **Gathering**: Resource collection areas (food, wood, stone, clay, gold)
  - Each gathering area produces one resource type
  - Capacity limits how many workers can gather

#### `player.py` - Player State
Tracks everything about a single player:

**Resources**:
- `resources`: Dict of resource types (2-6) → quantities
- `wheat`: Special currency for feeding
- `one_use_tools`: Consumable tools

**Workers**:
- `total_workers`: Workers available each round
- `available_workers`: Workers not yet placed this round

**Inventory**:
- `tools`: 4 persistent tool slots [value, available]
- `building_num`: Count of buildings owned
- `card_effects`: Collected cards in two decks

**Scoring**:
- `vp`: Direct victory points
- `vp_buildings`: Points from buildings
- `multipliers`: End-game point multipliers

**Methods**:
- `get_vp()`: Calculate total victory points including multipliers
- `feed()`: Consume food to feed workers (-10 VP if insufficient)
- `decide_action()`: Choose action (human input or AI)
- `decide_to_use_tool()`: Decide tool usage when gathering
- `choose_resources()`: Pick resources when offered choice

#### `building.py` - Purchasable Buildings
Buildings provide victory points and require specific resources:

- **Building**: Abstract base class
  - `is_able_to_buy()`: Check if player can afford

- **CertainBuilding**: Fixed resource requirements
  - Example: [6, 6, 3] requires specific resources
  - `is_able_to_buy()`: Validate exact resources available

- **FlexBuilding**: Flexible resource requirements
  - Example: Need 5 resources from ≤2 types
  - `is_able_to_buy()`: Validate total and variety constraints

#### `card.py` - Purchasable Cards
Cards provide immediate effects and end-game bonuses:

**Card Types**:
1. `add_resource`: Gain resources immediately
2. `dice_roll`: Roll dice for choices
3. `resources_with_dice`: Get resources based on dice
4. `add_vp`: Immediate victory points
5. `add_tool`: Gain tool
6. `add_wheat`: Gain wheat
7. `draw_card`: Draw another card
8. `one_use_tool`: Single-use tool
9. `any_2_resources`: Choose 2 resources

**Methods**:
- `immediate_effect()`: Get effect when purchased
- `end_game_effect()`: Get victory points at end
- `is_able_to_buy()`: Check if player can afford

#### `utility.py` - Special Locations
Permanent board locations with specific functions:

- **Farm**: Gain wheat
- **House**: Gain workers
- **Tool Shop**: Gain tools

#### `game.py` - Game Orchestration
Main controller managing complete game flow:

**Game State**:
- `players`: 4 Player objects
- `round`: Current round number
- `current_player_idx`: Active player index
- `locations`: All board areas (utilities, gatherings, cards, buildings)
- `cards`: Available cards for purchase (up to 4)
- `buildings`: Available buildings for purchase (up to 4)
- `cards_in_deck`: Cards remaining to draw
- `buildings_in_deck`: Buildings remaining by location

**Main Methods**:
- `start_game()`: Initialize game
- `run_game()`: Execute complete game
- `run_round()`: Execute one round (placement → resolution → feeding)
- `get_available_actions()`: Get valid placements
- `execute_an_action()`: Place workers at location
- `resolve_locations()`: Process location effects
- `apply_card_effect()`: Apply card bonuses
- `feed_players()`: Consume food, apply penalties
- `replenish_cards()/buildings()`: Restock board

**Neural Network Interface**:
- `get_state()`: Extract game state as numpy array
  - Fixed size: 149 elements
  - Includes: resources, tools, cards, board state, buildings, action encoding
  - Suitable for DQN network input

#### `agent.py` - RL Agent
Deep Q-Network agent that learns through self-play:

**Agent State**:
- `n_games`: Games played so far
- `epsilon`: Exploration rate (starts high, decreases)
- `gamma`: Discount factor for future rewards
- `memory`: Experience replay buffer (max 100,000)
- `model`: DQN neural network (to be implemented)
- `trainer`: Training utility (to be implemented)

**Methods**:
- `get_state()`: Extract game state
- `remember()`: Store experience in memory
- `train_short_memory()`: Immediate single-step training
- `train_long_memory()`: Batch training on sampled experiences
- `get_action()`: Epsilon-greedy action selection

**Training Loop**:
1. Get old state
2. Choose action (exploration vs exploitation)
3. Execute action → get reward & new state
4. Train short memory immediately
5. Store in long memory
6. When game ends: train long memory on batch
7. Repeat

## State Representation (149 elements)

The game state is flattened into a 149-element numpy array for neural network input:

```
Scalars (5):
  - round, wheat, total_workers, available_workers, vp

Resources (5):
  - food, wood, stone, clay, gold

Multipliers (4):
  - tools, buildings, workers, wheat

Tools (8):
  - 4 tools × [value, available]

One-use tools (4):
  - Single-use tool values (padded with 0s)

Card collections (16):
  - Deck 0: 8 slots
  - Deck 1: 8 slots

Board occupancy (64):
  - 16 locations × 4 players

Building deck (4):
  - Remaining buildings per location

Buildings (12):
  - 4 buildings × [requirement1, requirement2, requirement3]

Cards (20):
  - Deck size + 4 cards × [type, cost, painting, data1, data2]

Action encoding (6):
  - Current action type representation

Total: 5 + 5 + 4 + 8 + 4 + 16 + 64 + 4 + 12 + 20 + 6 = 148
  (Note: Current implementation shows 149, verify calculation)
```

## File Structure

```
StoneAgeAI/
├── area.py          # Location base class (Gathering, etc.)
├── building.py      # Building implementations
├── card.py          # Card implementations
├── player.py        # Player state and decisions
├── utility.py       # Utility locations
├── game.py          # Game controller & state extraction
├── agent.py         # RL agent with DQN training
├── README.md        # This file
└── requirements.txt # Dependencies (to be created)
```

## Configuration Constants

### Agent (agent.py)
```python
MAX_MEMORY = 100000  # Experience replay buffer size
BATCH_SIZE = 1000    # Training batch size
LR = 0.001          # Learning rate
```

### Game (game.py)
- 4 players
- 3 utilities (Farm, House, Tool Shop)
- 5 gathering areas (food, wood, stone, clay, gold)
- Up to 4 cards on board
- Up to 4 buildings on board
- 10 rounds (configurable)

### Player (player.py)
- Starting food: 10
- Starting workers: 5
- Tool slots: 4
- Resource types: 5 (resources 2-6)

## Running the Game

### Basic Game Simulation
```python
from game import Game

game = Game()
game.start_game(seed=42)
game.run_game()
```

### RL Training
```python
from agent import Agent, train

# Runs training loop
train()

# Trains for N games with progress printing
# Saves model checkpoint when record score beaten
```

## Implementation Status

### ✅ Completed
- [x] Game state structure (players, resources, workers)
- [x] Area/Location classes (Gathering, Utility)
- [x] Building classes (Certain, Flex)
- [x] Card classes with effect types
- [x] Player resource/worker management
- [x] Game flow structure (rounds, turns, phases)
- [x] Worker placement mechanics
- [x] State extraction for neural network (149 elements)
- [x] Agent class with memory and training methods
- [x] Documentation for all modules

### 🔄 In Progress
- [ ] Location resolution (especially gathering mechanics)
- [ ] Card/building purchase logic refinement
- [ ] Dice roll implementations
- [ ] End-game scoring/VP calculation

### ⚠️ TODO
- [ ] DQN neural network model implementation
- [ ] Trainer class for optimization
- [ ] `play_ster()` method (main RL game loop)
- [ ] `reset()` method for agent
- [ ] Model saving/loading
- [ ] Proper game end conditions
- [ ] Random valid move selection
- [ ] Tool usage mechanics
- [ ] Wheat/food interaction details
- [ ] Testing and debugging

## Known Issues/Notes

1. **Method naming**: `play_ster()` appears to be a typo in agent.py
2. **get_state() verification**: Total elements shows 149, check calculation
3. **Game end condition**: Currently checks for None locations (incomplete)
4. **Tool mechanics**: Reset mechanism needed after round
5. **Random move selection**: `get_random_valid_move()` needs implementation
6. **AI decision methods**: Placeholder implementations in Player

## Dependencies

```
python >= 3.8
numpy
torch
gymnasium
```

## Training Tips

1. **Epsilon decay**: Currently decreases from 80 to 0 linearly over games
2. **Memory size**: Large buffer (100k) good for stability
3. **Batch size**: 1000 experiences per training step
4. **Learning rate**: 0.001 - may need tuning

## Architecture Decisions

1. **Fixed-size state**: 149-element array allows standard neural network input
2. **Experience replay**: Breaks correlation between sequential experiences
3. **DQN over PPO**: Better for discrete action spaces (8 locations)
4. **Modular design**: Each game component is independent
5. **Numpy for state**: Efficient and compatible with PyTorch

## Future Improvements

1. **Dueling DQN**: Separate value and advantage streams
2. **Double DQN**: Reduce overestimation bias
3. **Prioritized experience replay**: Sample important experiences more
4. **Multi-step returns**: Look further ahead in rewards
5. **Curriculum learning**: Start with simplified game, add complexity
6. **Self-play matchups**: Tournament evaluation between agent versions

## Testing

```python
# Test game initialization
game = Game()
assert len(game.players) == 4
assert len(game.locations) == 16  # 3 utilities + 5 gatherings + 4 cards + 4 buildings

# Test state extraction
state = game.get_state()
assert state.shape == (149,)
assert state.dtype == np.float32
```

## Contributing

When adding new features:
1. Add comprehensive docstrings
2. Update this README
3. Maintain modular design
4. Test with game simulation
5. Verify state extraction compatibility

## License

Internal research project

## Contact

For questions about implementation details, see docstrings in each module.