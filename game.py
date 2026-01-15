"""
Game module for Stone Age board game orchestration.

This module provides the main Game class that orchestrates the Stone Age board
game. It manages game flow (rounds, player turns), board state (locations, cards,
buildings), and game mechanics (worker placement, resource gathering, purchasing).

The game is designed to support both human and AI players. It can be used for
testing game logic or training a reinforcement learning agent.

Classes:
    Game: Main game controller managing all game state and mechanics.
"""

from typing import List, Dict, Optional, Any
import random
import numpy as np

from area import Gathering
from player import Player
from building import CertainBuilding, FlexBuilding, Building
from card import Card
from utility import Utility


class Game:
    """
    Main Stone Age game controller.
    
    Manages complete game state and orchestrates game flow including:
    - Round progression
    - Player turns
    - Worker placement
    - Location resolution (resource gathering, building purchases)
    - End-game scoring
    
    The game supports up to 4 players and includes configurable cards, buildings,
    and utilities. Game state can be extracted as a numpy array for RL training.
    
    Attributes:
        players (List[Player]): The 4 players in the game.
        round (int): Current round number (starts at 0).
        current_player_idx (int): Index of player whose turn it is.
        cards (List[Card]): Cards available for purchase on the board.
        buildings (List[Building]): Buildings available for purchase.
        locations (List): All board locations (utilities, gatherings, cards, buildings).
        cards_in_deck (List[Card]): Remaining cards in deck to draw from.
        buildings_in_deck (Dict[int, List[Building]]): Remaining buildings per location.
        first_player (int): Index of the starting player this round.
        current_type_of_action (list): Encoded action state for neural network.
    """
    
    def __init__(self) -> None:
        """
        Initialize a new game with 4 players and standard board setup.
        
        Sets up:
        - 4 players with default resources
        - 8 locations (3 utilities + 5 gathering areas)
        - 4 cards available for purchase
        - 4 buildings available for purchase
        - Deck of cards and buildings for replenishment
        """
        # Initialize 4 players
        self.players: List[Player] = (Player(), Player(), Player(), Player())
        
        # Game state tracking
        self.round = 0
        self.current_player_idx = 0
        
        # Cards available on board (up to 4)
        self.cards: List[Card] = [
            Card("add_resource", cost=1, data={"resources": 2, "amount": 8}),
            Card("add_resource", cost=2, data={"resources": 2, "amount": 8}),
            Card("add_resource", cost=3, data={"resources": 2, "amount": 8}),
            Card(card_type="add_resource", cost=4, data={"resources": 2, "amount": 8}),
        ]
        
        # Buildings available on board (up to 4)
        self.buildings: List[Building] = [
            CertainBuilding(resources=[6, 6, 3]),
            FlexBuilding(resources_require_count=5, variety=2),
            CertainBuilding(resources=[3, 4, 3]),
            CertainBuilding(resources=[6, 5, 4]),
        ]
        
        # All board locations in order:
        # Indices 0-2: Utilities
        # Indices 3-7: Gathering areas  
        # Indices 8-11: Cards
        # Indices 12-15: Buildings
        self.locations: List[Optional[Any]] = [
            Utility("Farm", 1),           # Gain wheat
            Utility("House", 2),          # Gain workers
            Utility("ToolShop", 1),       # Gain tools
            Gathering(40, 2),             # Food (resource 2)
            Gathering(7, 3),              # Wood (resource 3)
            Gathering(7, 4),              # Stone (resource 4)
            Gathering(7, 5),              # Clay (resource 5)
            Gathering(7, 6),              # Gold (resource 6)
        ]
        
        # Add cards and buildings to locations
        self.locations.extend(self.cards)
        self.locations.extend(self.buildings)
        
        # Deck of cards to draw from when cards are purchased
        self.cards_in_deck: List[Card] = [
            Card("add_resource", cost=1, data={"resources": 2, "amount": 8}),
            Card("add_resource", cost=1, data={"resources": 2, "amount": 8}),
        ]
        
        # Deck of buildings by location index
        self.buildings_in_deck: Dict[int, List[Building]] = {
            12: [CertainBuilding(resources=(3, 4, 3)), CertainBuilding(resources=(3, 4, 3))],
            13: [CertainBuilding(resources=(3, 4, 3)), CertainBuilding(resources=(3, 4, 3))],
            14: [CertainBuilding(resources=(3, 4, 3)), CertainBuilding(resources=(3, 4, 3))],
            15: [CertainBuilding(resources=(3, 4, 3)), CertainBuilding(resources=(3, 4, 3))],
        }
        
        # Game flow tracking
        self.first_player = 0
        
        # Encoded action state for neural network (used in get_state())
        # Represents the current type of action being performed
        self.current_type_of_action = [1, 0, 0, 0, 0]

    @property
    def current_player(self) -> Player:
        """
        Get the Player object for the current player.
        
        Returns:
            Player: The player whose turn it currently is.
        """
        return self.players[self.current_player_idx]

    def start_game(self, seed: Optional[int] = None) -> None:
        """
        Prepare the game for play.
        
        Initializes all players with starting resources and optionally sets
        a random seed for reproducibility.
        
        Args:
            seed (int, optional): Random seed for reproducible games.
        """
        if seed is not None:
            random.seed(seed)
        
        # Reset workers for all players
        for p in self.players:
            p.total_workers = 5
            p.available_workers = 5
        
        print(f"Game started with {len(self.players)} players")

    def run_game(self) -> None:
        """
        Execute a complete game from start to finish.
        
        Runs rounds until game end condition (typically when the board
        becomes full or all cards/buildings are exhausted).
        """
        while self.game_not_ended():
            self.run_round()
            # Rotate starting player for next round
            self.first_player = (self.first_player + 1) % len(self.players)

    def game_not_ended(self) -> bool:
        """
        Determine if the game should continue.
        
        Currently checks if any location is None (indicating space on board).
        This is a placeholder condition that should be refined.
        
        Returns:
            bool: True if game should continue, False if game is over.
        """
        # TODO: Implement proper game end condition
        # Current logic seems incomplete - all locations are initialized
        return any(location is None for location in self.locations)

    def run_round(self) -> None:
        """
        Execute a complete round of Stone Age.
        
        Rounds follow this structure:
        1. PLACEMENT PHASE: Players take turns placing workers
        2. RESOLUTION PHASE: Each location resolves (workers gather/buy)
        3. FEEDING PHASE: Players pay food to feed workers
        4. REPLENISHMENT PHASE: Restock cards and buildings
        
        The first player changes each round (rotating), and unused workers
        are refreshed at the end.
        """
        self.round += 1
        print(f"== Starting Round {self.round} ==")
        
        # ===== PLACEMENT PHASE =====
        # Clear all locations at round start
        for area in self.locations:
            area.clear()
        
        # Players take turns placing workers until all are placed
        while self.round_not_over():
            if self.current_player.available_workers > 0:
                # Keep asking for action until valid move is made
                action_is_not_valid = True
                while action_is_not_valid:
                    available_actions = self.get_available_actions()
                    action = self.current_player.decide_action(available_actions)
                    action_is_not_valid = self.execute_an_action(action)
            
            self.next_player()

        # ===== RESOLUTION PHASE =====
        # Reset to first player for resolution
        self.current_player_idx = self.first_player
        
        # Each player resolves their placed workers
        for _ in range(len(self.players)):
            self.resolve_locations()
            self.next_player()
        
        # ===== FEEDING PHASE =====
        # Players pay food for workers
        self.feed_players()
        
        # ===== REPLENISHMENT PHASE =====
        # Reset workers and restock board
        self.refresh_humans()
        self.get_new_buildings_and_cards()

    def get_available_actions(self) -> list:
        """
        Get all valid actions available to current player depending
        on a self.current_type_of_action

        [0] = 1 Means its time to place workers
        [1] = 1 Means its time to decide to use or not tools on a resources
        [2] = 1 Means its time to decide buy or not building
        [3] = 1 Means its time to decide which resources to spend for Flex Building or Card
        [4] = 1 Means its time to decide which die to choose a die on a civilization Card
        
        Returns:
            list: List of available actions, each containing:
                [location_index, available_space, location_name]
        """
        available_actions = []
        index = 0
        if self.current_type_of_action[0] == 1:
            for location in self.locations:
                # Check if location has space and can accept placements
                if location is not None and location.can_place():
                    available_actions.append([
                        index,
                        location.available_space(),
                        location.name()
                    ])
                index += 1
            return available_actions
        elif self.current_type_of_action[1] == 1:
            self.avaliable_tools = []
            for index, tool in enumerate(self.current_player.tools):
                if tool[1] == True:
                    available_actions.append(index)
                one_use_tools = len(self.current_player.one_use_tools)

    def execute_an_action(self, action: Any) -> bool:
        """
        Execute a player's chosen action (place workers at a location).
        
        Validates the action against current game state:
        - Location must have space
        - Player must have enough available workers
        - Must be a positive number of workers
        
        Args:
            action (Any): Action tuple [location_index, worker_count].
        
        Returns:
            bool: True if action failed validation, False if successful.
        """
        if (self.locations[action[0]].can_place(action[1]) and 
            self.current_player.available_workers >= action[1] and 
            action[1] > 0):
            
            print(f"Player {self.current_player_idx} executes action {action}")
            self.place_worker(action[0], action[1])
            return False  # Action succeeded
        
        return True  # Action failed validation

    def round_not_over(self) -> bool:
        """
        Check if the placement phase is still ongoing.
        
        The placement phase continues as long as any player has available
        workers to place.
        
        Returns:
            bool: True if any player has workers to place, False if all done.
        """
        return any(p.available_workers > 0 for p in self.players)

    def place_worker(self, location_id: int, count: int = 1) -> None:
        """
        Place workers for current player at a specific location.
        
        Updates the location's occupancy and decreases player's available workers.
        
        Args:
            location_id (int): Index of the location on the board.
            count (int): Number of workers to place (default: 1).
        """
        print(f"Player {self.current_player_idx} places {count} worker(s) at location {location_id}")
        
        # Update location occupancy
        self.locations[location_id].place(self.current_player_idx, count)
        
        # Update player's available workers
        self.current_player.available_workers -= count

    def next_player(self) -> Player:
        """
        Move turn to the next player.
        
        Returns:
            Player: The next player whose turn it is.
        """
        self.current_player_idx = (self.current_player_idx + 1) % len(self.players)
        return self.current_player

    def resolve_locations(self) -> None:
        """
        Resolve all occupied locations for the current player.
        
        For each location where current player has workers, applies the location's
        effects (gather resources, offer building purchase, grant special bonuses).
        
        Different location types have different resolution:
        - Utility: Immediate reward (wheat, workers, tools)
        - Gathering: Collect resources (amount based on workers placed)
        - Building: Player chooses whether to purchase
        - Card: Player chooses whether to purchase
        """
        print(f"Resolving locations for player {self.current_player_idx}")
        
        for location in self.locations:
            if location is None or not location.is_occupied(self.current_player_idx):
                continue

            # ===== UTILITY RESOLUTION =====
            if isinstance(location, Utility):
                print(f"  Utility resolved: {location.name()}")
                if location.name() == "Farm":
                    self.current_player.get_wheat(1)
                elif location.name() == "House":
                    self.current_player.get_worker(1)
                elif location.name() == "ToolShop":  # Note: original had "Tools"
                    self.current_player.get_tool()

            # ===== GATHERINH RESOLUTION =====
            elif isinstance(location, Gathering):
                if location.is_occupied(self.current_player_idx):
                    self.resolve_gathering(location)

            # ===== CARD RESOLUTION =====
            elif isinstance(location, Card):
                result = self.current_player.decide_to_buy_flex_build_card(
                    location.cost,
                    4,
                    True
                )
                if result[1]:  # If player confirmed purchase
                    print(f"Player {self.current_player_idx} buys card {location}")
                    self.current_player.get_card(location.end_game_effect())
                    self.current_player.lose_resources(result[0])
                    self.buy_card(location)
            
            # ===== FLEX BUILDING RESOLUTION =====
            elif isinstance(location, FlexBuilding):
                result = self.current_player.decide_to_buy_flex_build_card(
                    location.resources_require_count,
                    location.variety,
                    False
                )
                if result[1]:  # If player confirmed purchase
                    print(f"  Player {self.current_player_idx} buys {location}")
                    self.current_player.lose_resources(location.resources)
                    self.current_player.vp_buildings += sum(v for v in result[0])
                    self.buy_building(location)
            
            # ===== CERTAIN BUILDING RESOLUTION =====
            elif isinstance(location, CertainBuilding):
                if self.current_player.decide_to_buy_build():
                    print(f"Player {self.current_player_idx} buys {location}")
                    self.current_player.vp_buildings += sum(v for v in location.resources)
                    self.current_player.lose_resources(location.resources)
                    self.buy_building(location)
            

    def resolve_gathering(self, location: Gathering) -> None:
        """
        Resolve a gathering location (collect resources).
        
        Calculates how much of a resource the player gathers based on:
        - Number of workers placed at the location
        - Resource type and availability
        - Player's tools (if used)
        
        Args:
            location (Gathering): The gathering area being resolved.
        """
        worker_count = location.occupants[self.current_player_idx]
        
        # Dice roll determines base amount
        # TODO: Implement proper gathering logic with tool usage
        base_amount = sum(random.randint(1, 6) for _ in range(worker_count))
        
        # Apply tool bonuses
        # TODO: Call decide_to_use_tool and modify base_amount
        
        # Grant resources
        self.current_player.get_resource_with_die(location.resource_type, base_amount)

    def apply_card_effect(self, card: Card) -> None:
        """
        Apply a card's immediate effect to the current player.
        
        Different card types have different effects:
        - add_resource: Grant resources
        - dice_roll: Offer dice-based reward choices
        - resources_with_dice: Roll dice for resource gathering
        - add_vp: Grant victory points
        - add_tool: Grant tools
        - add_wheat: Grant wheat
        - draw_card: Draw another card
        - one_use_tool: Grant single-use tool
        - any_2_resources: Let player choose 2 resources
        
        Args:
            card (Card): The card whose effect is being applied.
        """
        effect_type = card.card_type
        effect = card.immediate_effect()
        
        if effect_type == "add_resource":
            # Grant specified resources
            resource_type = effect[0]
            resource_amount = effect[1]
            self.current_player.get_resources(resource_type, resource_amount)
        
        elif effect_type == "dice_roll":
            # Roll dice for each player and offer choices
            dices = self.roll_dice_separate(len(self.players))
            self.current_player.choose_reward_and_apply(dices)
            for _ in range(len(self.players) - 1):
                self.next_player().choose_reward_and_apply(dices)
            self.next_player()
        
        elif effect_type == "resources_with_dice":
            # Roll dice and gather specific resource
            dice_sum = sum(random.randint(1, 6) for _ in range(2))
            resource_type = effect[0]
            dice_sum = self.current_player.decide_to_use_tool(dice_sum, resource_type)
            amount = dice_sum // resource_type
            self.current_player.resources[resource_type] += amount
        
        elif effect_type == "add_vp":
            # Award victory points
            self.current_player.vp += effect[0]
        
        elif effect_type == "add_tool":
            # Grant tool
            self.current_player.get_tool()
        
        elif effect_type == "add_wheat":
            # Grant wheat
            self.current_player.get_wheat(1)
        
        elif effect_type == "draw_card":
            # Draw and apply another card
            card = self.draw_card()
            if card is not None:
                self.current_player.get_card(card.end_game_effect())
        
        elif effect_type == "one_use_tool":
            # Grant single-use tool
            self.current_player.get_one_use_tool(effect[0])
        
        elif effect_type == "any_2_resources":
            # Let player choose 2 resources to gain
            self.current_player.choose_resources(2)
            self.current_player.get_resources(2, 2)

    def feed_players(self) -> None:
        """
        End-of-round feeding phase.
        
        Each player must feed their workers, consuming food. Wheat can help.
        Penalty of -10 VP if player cannot afford to feed everyone.
        """
        for player in self.players:
            player.feed()

    def get_new_buildings_and_cards(self) -> None:
        """
        Replenish the board with new cards and buildings.
        
        Called at end of round to replace purchased cards and buildings.
        """
        self.replenish_buildings()
        self.replenish_cards()

    def replenish_buildings(self) -> None:
        """
        Replace purchased buildings with new ones from the deck.
        
        Scans the buildings list for None entries (purchased buildings)
        and draws new buildings to replace them.
        """
        for index, building in enumerate(self.buildings):
            if building is None:
                self.draw_building(index)

    def replenish_cards(self) -> None:
        """
        Replace purchased cards with new ones from the deck.
        
        Shifts remaining cards to fill gaps and draws new cards to
        maintain the card display.
        """
        # Find empty slots
        empty_index = []
        for index, card in enumerate(self.cards):
            if card is None:
                empty_index.append(index)
            # Shift remaining cards into empty slots
            elif empty_index:
                self.replace_card(empty_index.pop(0), card)
        
        # Fill remaining empty slots with new cards from deck
        for index in empty_index:
            self.replace_card(index, self.draw_card())

    def replace_card(self, index: int, new_card: Card) -> None:
        """
        Replace a card at a specific index.
        
        Updates both the cards list and the locations list.
        
        Args:
            index (int): Index in the cards list (0-3).
            new_card (Card): The new card to place.
        """
        self.cards[index] = new_card
        # Card locations start at index 8 in locations list
        self.locations[8 + index] = new_card

    def replace_building(self, index: int, new_building: Building) -> None:
        """
        Replace a building at a specific index.
        
        Updates both the buildings list and the locations list.
        
        Args:
            index (int): Index in the buildings list (0-3).
            new_building (Building): The new building to place.
        """
        self.buildings[index] = new_building
        # Building locations start at index 12 in locations list
        self.locations[12 + index] = new_building

    def buy_building(self, building: Building) -> None:
        """
        Mark a building as purchased (remove from board).
        
        Sets the building to None, which will trigger replenishment.
        Also increments the current player's building count.
        
        Args:
            building (Building): The building being purchased.
        """
        # Find and remove the building
        for i, b in enumerate(self.buildings):
            if b is building:
                self.buildings[i] = None
                self.locations[12 + i] = None
                break
        
        # Track ownership
        self.current_player.building_num += 1

    def buy_card(self, card: Card) -> None:
        """
        Mark a card as purchased (remove from board).
        
        Sets the card to None, which will trigger replenishment.
        
        Args:
            card (Card): The card being purchased.
        """
        # Find and remove the card
        for i, c in enumerate(self.cards):
            if c is card:
                self.cards[i] = None
                self.locations[8 + i] = None
                break

    def refresh_humans(self) -> None:
        """
        Refresh worker availability at round end.
        
        Called after feeding phase to reset available workers for next round.
        """
        for p in self.players:
            p.available_workers = p.total_workers

    def draw_card(self) -> Optional[Card]:
        """
        Draw a card from the deck.
        
        Returns:
            Card: The drawn card, or None if deck is empty.
        """
        if self.cards_in_deck:
            card = self.cards_in_deck.pop(0)
            print(f"Drew card: {card}")
            return card
        print("No card to draw")
        return None

    def draw_building(self, location_id: int) -> Optional[Building]:
        """
        Draw a building for a specific board location.
        
        Args:
            location_id (int): Index of the building location (0-3).
        
        Returns:
            Building: The drawn building, or None if deck is empty.
        """
        if location_id in self.buildings_in_deck and self.buildings_in_deck[location_id]:
            b = self.buildings_in_deck[location_id].pop(0)
            print(f"Drew building for location {location_id}: {b}")
            self.replace_building(location_id, b)
            return b
        print(f"No building to draw for location {location_id}")
        return None

    def roll_dice_separate(self, count: int) -> list:
        """
        Roll separate dice for players to choose from.
        
        Args:
            count (int): Number of dice to roll.
        
        Returns:
            list: List of dice rolls.
        """
        return [random.randint(1, 6) for _ in range(count)]

    def get_state(self) -> np.ndarray:
        """
        Extract the current game state as a fixed-size numpy array.
        
        Converts complex game state into a 1D array suitable for neural network
        input. The array includes:
        - Game metadata (round, VP, workers)
        - Player resources (food, wood, stone, clay, gold)
        - Player tools (value + availability for each slot)
        - Player card collections
        - Board occupancy (workers at each location)
        - Building deck sizes
        - Available cards info
        - Action encoding
        
        Total size: 148 elements (must match network input size)
        
        Returns:
            np.ndarray: 1D array of float32 values representing game state.
        """
        # Extract current player state
        resources = list(self.current_player.resources.values())
        tools = self.current_player.tools
        one_use_tools = self.current_player.one_use_tools
        multipliers = list(self.current_player.multipliers.values())
        wheat = self.current_player.wheat
        drawings = self.current_player.card_effects
        total_workers = self.current_player.total_workers
        available_workers = self.current_player.available_workers

        flat_state = []

        # === Scalars (5) ===
        flat_state.append(self.round)
        flat_state.append(wheat)
        flat_state.append(total_workers)
        flat_state.append(available_workers)
        flat_state.append(self.current_player.get_vp())

        # === Resources (5) ===
        flat_state.extend(resources)

        # === Multipliers (4) ===
        flat_state.extend(multipliers)

        # === Tools (8) ===
        # Each tool slot: [value, availability_as_0_or_1]
        for tool in tools:
            flat_state.append(tool[0])
            flat_state.append(1 if tool[1] else 0)

        # === One-use tools (4) ===
        # Pad with zeros if fewer than 4
        MAX_ONE_USE_TOOLS = 4
        for i in range(MAX_ONE_USE_TOOLS):
            flat_state.append(one_use_tools[i] if i < len(one_use_tools) else 0)

        # === Card Drawings (16) ===
        # Track cards in two decks (8 slots each)
        MAX_DECK_0_CARDS = 8
        MAX_DECK_1_CARDS = 8

        # Deck 0 cards
        for i in range(MAX_DECK_0_CARDS):
            flat_state.append(drawings[0][i] if i < len(drawings[0]) else 0)

        # Deck 1 cards
        for i in range(MAX_DECK_1_CARDS):
            flat_state.append(drawings[1][i] if i < len(drawings[1]) else 0)

        # === Board state (16 locations × 4 players = 64) ===
        # Track worker count for each player at each location
        for area in self.locations:
            if area is not None:
                flat_state.extend(area.occupants.values())
            else:
                # Null location: 0 workers from each player
                flat_state.extend([0, 0, 0, 0])

        # === Building deck sizes (4) ===
        for deck in self.buildings_in_deck.values():
            flat_state.append(len(deck))

        # === Buildings (4 × 3 = 12) ===
        # Encode building requirements
        for building in self.buildings:
            if building is None:
                flat_state.extend([0, 0, 0])
            elif isinstance(building, FlexBuilding):
                flat_state.extend([building.resources_require_count, building.variety, 0])
            else:
                flat_state.extend(building.resources)

        # === Cards (4 × 5 = 20) ===
        # Include deck size + 4 cards × 5 features
        flat_state.append(len(self.cards_in_deck))
        for card in self.cards:
            if card is None:
                flat_state.extend([0, 0, 0, 0, 0])
            else:
                # Extract card data
                card_data: list[int] = [0, 0]
                if card.data is not None:
                    card_data = list(card.data.values())
                    if len(card_data) != 2:
                        card_data.append(0)
                
                flat_state.extend([
                    card.card_type_num,
                    card.cost,
                    card.painting or 0
                ])
                flat_state.extend(card_data)

        # === Action encoding (6) ===
        flat_state.extend(self.current_type_of_action)

        # === Total (148) ===
        return np.array(flat_state, dtype=np.float32)

    def get_random_valid_move(self) -> list:
        """
        Get a random valid action for the current player.
        
        Used for random exploration in RL or testing.
        
        Returns:
            list: Random action [location_index, worker_count].
        """
        actions = self.get_available_actions()
        if not actions:
            return [0, 0]
        action = random.choice(actions)
        return action[:2]

    # TODO: Implement missing methods
    # - play_ster(): Main game loop for RL training
    # - reset(): Reset game state for next episode
    # - get_random_legal_action(): Better random move selection