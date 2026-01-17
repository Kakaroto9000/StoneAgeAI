# StoneAgeAI Development Guide for AI Agents

## Project Overview
StoneAgeAI is a reinforcement learning-based game engine implementing a Stone Age board game with multiple players, strategic resource management, and AI decision-making. The codebase is under active development with a focus on game mechanics, player intelligence, and ML integration.

## Architecture

### Core Game Flow (`game.py`)
- **Central orchestrator** managing game state: players, cards, buildings, and locations
- Initializes with 4 players, multiple location types (utilities, gathering areas, cards, buildings)
- Maintains game round tracking and current player index
- Key data structures:
  - `locations`: List of Area subclasses (utilities, gathering, cards, buildings)
  - `cards_in_deck` / `buildings_in_deck`: Card/building pools
  - `players`: List of Player objects

### Entity Hierarchy - Area Abstract Base Class (`area.py`)
All game locations inherit from `Area(ABC)`:
- **Attributes**: `capacity` (max workers), `occupants` (dict of player_id → worker_count)
- **Subclasses**:
  - `Utility`: Named utility locations (Farm, House, ToolShop) with fixed capacity
  - `Gathering`: Resource extraction with resource_type and high capacity
  - `Card`: Game cards with costs, types, and effects (see `card.py`)
  - `Building`: Structures with resource requirements (see `building.py`)

### Player State Management (`player.py`)
- **Resources**: Dictionary keyed by numeric IDs (2=food, 3=wood, 4=stone, 5=clay, 6=gold)
- **Workers**: `total_workers` vs `available_workers` tracking (placement mechanic)
- **Tools**: `tools` array (4 tool slots with [level, available]) + `one_use_tools` list
- **Decision Point**: `decide_action()` - branches on `AI` flag:
  - `AI=False`: Human input via `input()`
  - `AI=True`: Delegates to Agent logic (to be implemented)
- **Action Methods**: `get_resource_with_die()`, `decide_to_buy_flex_build_card()` implement game mechanics

### Card System (`card.py`)
- **Types**: String-based (e.g., "add_resource", "resources_with_dice", "civilization") mapped to numeric IDs in `CARD_TYPE_NUMBERS`
- **Mechanics**:
  - `immediate_effect()`: Instant card benefits (resources, tools, VP)
  - `end_game_effect()`: Scoring multipliers (civilization cards use `multiplier` or `painting`)
  - `is_able_to_buy()`: Players need sufficient resource total ≥ `cost`

### Building Acquisition (`building.py`)
- **CertainBuilding**: Requires specific resource counts (tuple-based requirements)
- **FlexBuilding**: Requires `resources_require_count` from ≥ `variety` different resource types
- Both implement `is_able_to_buy(player_resources)` for purchase validation

### Machine Learning Layer (`agent.py`)
- **Imports**: `torch`, `numpy`, `deque` for neural network training
- **Hyperparameters**: `Max_Memory=100000`, `Batch_size=1000`, `LR=0.001`
- **Currently Incomplete**: Stub implementation - needs DQN or similar RL algorithm

## Key Patterns & Conventions

1. **Resource Enumeration**: Always use numeric IDs (2-6) not strings. Resource type 2 is food baseline.
2. **Worker Placement**: Validate with `Area.can_place()` and `avaliable_space()` before placement.
3. **Capacity Management**: Areas have hard capacity limits; check `occupants` dict sum before placing workers.
4. **Action Decision Pattern**: Check `player.AI` flag to route between human input and agent logic.
5. **Dictionary-based State**: Player resources, occupants, tools use dicts for flexible indexing.

## Critical Developer Workflows

- **Running Game**: Execute `game.py` directly (no test framework found; manual testing)
- **AI Integration**: Implement `Agent` class methods to handle `Player.decide_action()` return values
- **Adding New Cards**: Add type to `CARD_TYPE_NUMBERS`, implement effects in `immediate_effect()` / `end_game_effect()`
- **Debugging Player State**: Use `player.resources` and `player.available_workers` to inspect state

## Cross-File Dependencies
- `game.py` → imports all entity types (Player, Card, Building, Area, Gathering, Utility)
- `player.py` → no external imports (isolated state)
- `card.py`, `building.py` → inherit from `Area` (see `area.py`)
- `agent.py` → imports `Player`, `deque`; expects to be called by game loop

## Next Priority Areas
- Complete `Agent` RL algorithm (currently DQN parameters defined but no implementation)
- Implement `Player.decide_action()` logic for AI players
- Map additional game mechanics from incomplete stubs in `game.py`
