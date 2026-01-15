StoneAgeAI
A reinforcement learning agent that learns to play the Stone Age board game through self-play using Deep Q-Networks (DQN).
Quickstart
bash# Install dependencies
pip install torch numpy gymnasium

# Run training
python agent.py

# Watch a game (after training)
python agent.py --play
Project Structure
stone_age/
├── agent.py      # DQN agent + training loop
├── game.py       # Game orchestration + state extraction
├── player.py     # Player state + decisions
├── area.py       # Board locations (base class)
├── building.py   # Purchasable buildings
├── card.py       # Purchasable cards
└── utility.py    # Special locations (farm, house, tool shop)
Architecture
┌─────────────────────────────────────────────────────────────────┐
│                         TRAINING LOOP                           │
│  ┌─────────┐    state     ┌─────────┐    action    ┌─────────┐ │
│  │  Game   │─────────────▶│  Agent  │─────────────▶│  Game   │ │
│  │ State   │              │  (DQN)  │              │play_step│ │
│  └─────────┘              └─────────┘              └────┬────┘ │
│       ▲                        │                        │      │
│       │                   remember()                    │      │
│       │                        │                        ▼      │
│       │                        ▼               reward, done    │
│       │                  ┌─────────┐                    │      │
│       └──────────────────│ Memory  │◀───────────────────┘      │
│                          │ Buffer  │                           │
│                          └─────────┘                           │
└─────────────────────────────────────────────────────────────────┘
How It Works
1. Game State → Neural Network Input
The game state is flattened into a 143-element vector:
ComponentSizeDescriptionScalars5round, wheat, total_workers, available_workers, VPResources5food, wood, stone, clay, goldMultipliers4tools, buildings, workers, wheatTools84 slots × [value, available]One-use tools4padded to max 4Card effects162 decks × 8 cards maxBoard state6416 locations × 4 playersBuilding decks4cards remaining per deckBuildings124 buildings × [count, variety, 0]Cards21deck_size + 4 cards × 5 valuesTotal143
2. Neural Network Architecture
Input (143) → Linear(256) → ReLU → Linear(128) → ReLU → Output(16)
                                                           │
                                              Q-values for 16 locations
3. Action Space
The agent chooses which location to place workers (0-15):
IndexLocation TypeEffect0Farm+1 wheat1House+1 worker2Tool Shop+1 tool level3-7GatheringCollect resources (food/wood/stone/clay/gold)8-11CardsPurchase civilization cards12-15BuildingsPurchase buildings for VP
4. Reward Signal
pythonreward = (new_vp - old_vp)           # VP gained this turn
       + 0.1 * resources_gained      # Small bonus for resources
       - 10 if starved else 0        # Penalty for not feeding workers
       + 50 if won else 0            # Bonus for winning
       
Key Classes
Game
pythongame = Game()                    # Initialize 4-player game
state = game.get_state()         # Get 143-element numpy array
actions = game.get_available_actions()  # Legal moves
reward, done, score = game.play_step(action)  # Execute action
game.reset()                     # New game
Agent
pythonagent = Agent()
state = agent.get_state(game)              # Extract state
action = agent.get_action(state)           # Choose action (ε-greedy)
agent.remember(state, action, reward, next_state, done)
agent.train_short_memory(...)              # Train on single experience
agent.train_long_memory()                  # Train on batch from replay buffer
Player
pythonplayer.resources      # {2: food, 3: wood, 4: stone, 5: clay, 6: gold}
player.tools          # [[value, available], ...] × 4 slots
player.one_use_tools  # [value, ...] consumable tools
player.multipliers    # {'tools': 0, 'buildings': 0, 'workers': 0, 'wheat': 0}
player.get_vp()       # Calculate total VP including multipliers
player.feed()         # Feed workers at round end
Training Tips

Start simple: Train against random opponents first
Epsilon decay: Start ε=0.8, decay to 0.01 over 1000 games
Batch size: 64-256 works well
Memory size: 100k experiences
Learning rate: 0.001 with Adam optimizer

Common Issues
ProblemCauseFixstate.shape mismatchVariable-length dataEnsure all lists are padded to fixed sizeindex out of rangeEmpty building deckCheck deck before drawingNaN lossLarge rewardsNormalize rewards to [-1, 1] rangeAgent always picks same actionLow explorationIncrease ε or use noisy networks
Game Rules Summary
Stone Age is a worker placement game where players:

Place workers at locations each round
Gather resources by rolling dice (sum ÷ resource type = amount)
Use tools to boost dice rolls
Buy buildings/cards for victory points
Feed workers at round end (1 food each, or -10 VP penalty)
Win by having most VP when a building deck empties

Next Steps
See DEVELOPMENT.md for:

Implementing the DQN network
Adding action masking for legal moves
Tool combination system
Multi-agent training