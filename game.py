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
from itertools import combinations_with_replacement
from typing import List, Dict, Optional, Any, Union
import random
import numpy as np
from action_system import ActionSystem, MaskGenerator


from itertools import product

from area import Gathering, Area
from player import Player
from building import CertainBuilding, FlexBuilding, Building
from card import Card
from utility import Utility
from decks import create_card_deck
from decks import create_building_decks


Location = Union[Utility, Gathering, Card, FlexBuilding, CertainBuilding, None]


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

        self.locations: List[Location] = [
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
        self.cards_in_deck: List[Card] = create_card_deck()
        
        # Deck of buildings by location index
        self.buildings_in_deck: Dict[int, List[Building]] = create_building_decks()
        
        # Game flow tracking
        self.first_player = random.randint(0,3)
        
        # Encoded action state for neural network (used in get_state())
        # Represents the current type of action being performed and data about this action if needed (for civilization cards and Flex buildings)
        self.current_type_of_action = 1
        self.current_action_data = [0,0,0,0]
        self.game_end = False

        self.action_system = ActionSystem(self.locations)
        self.mask_generator = MaskGenerator(self.action_system)
        

    def game_ended(self) -> bool:
        if self.round >= 50:
            return True
        # End if card deck AND all board card slots are empty
        if len(self.cards_in_deck) == 0 and any(c is None for c in self.cards):
            return True
        # End if any building stack is fully depleted
        for i, deck in self.buildings_in_deck.items():
            if len(deck) == 0 and self.buildings[i] is None:
                return True
        return False
                
    def get_valid_actions_for_choose_2_resources(self):
        all_actions = []
        for combo in product(range(2,7), repeat=2):
            all_actions.append(combo)
        return all_actions
            
    
    def get_valid_actions_for_placement(self):
        locations_space = []
        for index, location in enumerate(self.locations):
            # Check if location has space and can accept placements
            if location is not None and location.can_place():
                locations_space.append([
                    index,
                    min(location.available_space(), self.current_player.available_workers),
                ])

        all_actions = []

        # Is equivalent to:
        for loc_index, avaliable_space in locations_space:
            for i in range(1, avaliable_space+1):
                all_actions.append([loc_index,i])

        return all_actions
    
    def get_valid_actions_for_tools_choose(self):
        avaliable_tools = []
        all_actions = []
        for index, tool in enumerate(self.current_player.tools):
            if tool[1] == True and tool[0] > 0:
                avaliable_tools.append(index)
        for i in range(len(self.current_player.one_use_tools)):
            avaliable_tools.append(i+4)
        for combo in product([0, 1], repeat=len(avaliable_tools)):
            lst = [0] * 7
            for i, pos in enumerate(avaliable_tools):
                lst[pos] = combo[i]
            all_actions.append(lst)
        return all_actions

    def get_valid_actions_for_spending_resources(self) -> list[list[int]]:
        data = self.locations[self.current_action_data[0]]

        if not isinstance(data, (Building, Card)):
            raise Exception("Current action data isn't a flex building or a card")
                
        valid_actions = []

        if isinstance(data, Card):
            return self.get_variants_to_spend_resources(data.cost)
        
        
        if data.resources_require_count == 7:
            available = self.current_player.resources  # {3: 2, 4: 1, 5: 3, 6: 0}
    
            max_spend = min(7, sum(available.values()))
    
            for n in range(1, max_spend + 1):
                valid_actions.extend(self.get_variants_to_spend_resources(n))
        else:
            return self.get_variants_to_spend_resources(data.resources_require_count, data.variety)
    
        return valid_actions
    
    def get_variants_to_spend_resources(self, cost: int, fixed_variety: Optional[int] = None):
        available = self.current_player.resources  # {3: 2, 4: 1, 5: 3, 6: 0}
        resource_types = [3,4,5,6]
        
        valid_actions = []
        for combo in combinations_with_replacement(resource_types, cost):
            # Count each resource type in this combo
            counts = {r: combo.count(r) for r in resource_types}
            # Check if player can afford
            
            if fixed_variety is not None:
                # Count how many different types are used
                types_used = (fixed_variety == sum(1 for r in resource_types if counts[r] > 0))
            else:
                types_used = True
            
            if types_used and all(counts[r] <= available[r] for r in resource_types):
                # Convert to list format: [wood_count, clay_count, stone_count, gold_count]
                valid_actions.append([counts[r] for r in resource_types])
        return valid_actions

    def get_mask(self):
        """Generate binary mask for currently valid actions."""
        return self.mask_generator.get_mask(self)

    def executing_placing_workers(self, action: Any) -> bool:
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
            
            self.place_worker(action[0], action[1])
            return False  # Action succeeded
        
        raise Exception("Cant place there!!")  # Action failed validation

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
    
    def next_player_to_gather(self):
        self.current_player_idx = (self.current_player_idx + 1) % len(self.players)
        if self.current_player.available_workers == 0:
            self.next_player_to_gather()

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
        
        for index, location in enumerate(self.locations):
            if location is None or not location.is_occupied(self.current_player_idx):
                continue

            # ===== UTILITY RESOLUTION =====
            if isinstance(location, Utility):
                if location.name() == "Farm":
                    self.current_player.get_wheat(1)
                elif location.name() == "House":
                    self.current_player.get_worker(1)
                elif location.name() == "ToolShop":  # Note: original had "Tools"
                    self.current_player.get_tool()
                location.occupants[self.current_player_idx] = 0

            # ===== GATHERINH RESOLUTION =====
            elif isinstance(location, Gathering):
                self.current_type_of_action = 2
                worker_count = location.occupants[self.current_player_idx]
                self.current_action_data = [location.resource_type, sum(random.randint(1, 6) for _ in range(worker_count)),0,0]
                ##self.resolve_gathering()
                return

            # ===== CARD RESOLUTION =====
            elif isinstance(location, Card):
                self.current_type_of_action = 3
                self.current_action_data = [index,0,0,0]
                return
            
            # ===== FLEX BUILDING RESOLUTION =====
            elif isinstance(location, FlexBuilding):
                self.current_type_of_action = 3
                self.current_action_data = [index,0,0,0]
                return
                
            
            # ===== CERTAIN BUILDING RESOLUTION =====
            elif isinstance(location, CertainBuilding):
                self.current_type_of_action = 3
                self.current_action_data = [index,0,0,0]
                return
            
        if self.check_if_any_uncollectedhumans_left():
            self.next_player()
            self.resolve_locations()
        else:
            self.finish_round()
    
    def finish_round(self):
        self.feed_players()

        self.round += 1

        self.first_player = (self.first_player + 1) % len(self.players)
        # ===== REPLENISHMENT PHASE =====
        # Reset workers and restock board
        self.refresh_humans()
        self.get_new_buildings_and_cards()
        self.refresh_tools()



        self.current_action_data = [0,0,0,0]
        self.current_type_of_action = 1
        self.current_player_idx = self.first_player
        self.game_end = self.game_ended()

    def resolve_gathering(self, tools: list[int]) -> None:
        """
        Resolve a gathering location (collect resources).
        
        Calculates how much of a resource the player gathers based on:
        - location_index
        - Player's tools (if used)
        
        Args:
            location (Gathering): The gathering area being resolved.
        """
        
        self.current_player.get_resource_with_die(self.current_action_data[0], self.current_action_data[1], tools)

        if self.current_type_of_action == 2:
            self.locations[self.current_action_data[0]+1].occupants[self.current_player_idx] = 0


    def apply_card_effect(self, card: Card) -> None: #TODO implement AI logic
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
            self.resolve_locations()
        
        elif effect_type == "dice_roll":
            # Roll dice for each player and offer choices
            dices = self.roll_dice_separate(len(self.players))
            self.current_action_data = dices
            self.current_type_of_action = 5
        
        elif effect_type == "resources_with_dice":
            # Roll dice and gather specific resource
            dice_sum = sum(random.randint(1, 6) for _ in range(2))
            resource_type = effect[0]
            self.current_type_of_action = 2
            self.current_action_data = [resource_type, dice_sum, 0, 0]
        
        elif effect_type == "add_vp":
            # Award victory points
            self.current_player.vp += effect[0]
            self.resolve_locations()
        
        elif effect_type == "add_tool":
            # Grant tool
            self.current_player.get_tool()
            self.resolve_locations()
        
        elif effect_type == "add_wheat":
            # Grant wheat
            self.current_player.get_wheat(1)
            self.resolve_locations()
        
        elif effect_type == "draw_card":
            # Draw and apply another card
            card = self.draw_card()
            if card is not None:
                self.current_player.get_card(card.end_game_effect())
            self.resolve_locations()
        
        elif effect_type == "one_use_tool":
            # Grant single-use tool
            self.current_player.get_one_use_tool(effect[0])
            self.resolve_locations()
        
        elif effect_type == "any_2_resources":
            # Let player choose 2 resources to gain
            self.current_type_of_action = 6

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

    def replace_card(self, index: int, new_card: Optional[Card]) -> None:
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
        new_card.cost = index + 1

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

    def buy_building(self, building_index: Building, resources = None) -> None:
        """
        Mark a building as purchased (remove from board).
        
        Sets the building to None, which will trigger replenishment.
        Also increments the current player's building count.
        
        Args:
            building (Building): The building being purchased.
        """
        self.current_player.vp_buildings += sum(v for v in resources)
        # Find and remove the building
        self.buildings[building_index-12] = None
        self.locations[building_index] = None


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
        
        for location in self.locations:
            if location is not None:
                location.clear()

    def refresh_tools(self) -> None:
        for p in self.players:
            p.refresh_tools()


    def draw_card(self) -> Optional[Card]:
        """
        Draw a card from the deck.
        
        Returns:
            Card: The drawn card, or None if deck is empty.
        """
        if self.cards_in_deck:
            card = self.cards_in_deck.pop(0)
            return card
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
            self.replace_building(location_id, b)
            return b
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

        # === One-use tools (3) ===
        # Pad with zeros if fewer than 4
        MAX_ONE_USE_TOOLS = 3
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
                card_data = list(card.data.values())
                if card.data:
                    if len(card_data) != 2:
                        card_data.append(0)
                else:
                    card_data = [0,0]
                
                flat_state.extend([
                    card.card_type_num,
                    card.cost,
                    card.painting or 0
                ])
                flat_state.extend(card_data)

        # === Action encoding (5) ===
        flat_state.append(self.current_type_of_action)
        flat_state.extend(self.current_action_data)

        # === Total (146) ===
        return np.array(flat_state, dtype=np.float32)

    def play_step(self, action_index: int):

        action = self.action_system.get_action(action_index)

        player_active = self.current_player
        current_score = self.current_player.get_score()
        current_vp = self.current_player.get_vp()
        if self.current_type_of_action == 1:
            self.locations[action[0]].place(self.current_player_idx, action[1])
            self.current_player.available_workers -= action[1]
            if not self.round_not_over():
                self.current_player_idx = self.first_player
                self.resolve_locations()
            else:
                self.next_player_to_gather()
        elif self.current_type_of_action == 2 or self.current_type_of_action == 7:
            self.resolve_gathering(action)
            self.resolve_locations()
        elif self.current_type_of_action == 3:
            location = self.locations[self.current_action_data[0]]
            can_afford = location.is_able_to_buy(self.current_player.resources)
            choice = "BUY" if action[0] == 1 else "SKIP"
            resources = {k: v for k, v in self.current_player.resources.items() if k != 2}
            print(f"  Buy/Skip: {choice}, can_afford={can_afford}, resources={resources}")
            if action[0] == 1:  # Buy
                location = self.locations[self.current_action_data[0]]
                if isinstance(location, CertainBuilding):
                    self.buy_building(self.current_action_data[0], location.resources)
                    self.resolve_locations()
                elif isinstance(location, Card):
                    self.buy_card(location)
                    self.apply_card_effect(location)
                    self.resolve_locations()
                else:  # FlexBuilding
                    self.current_type_of_action = 4
            else:
                self.locations[self.current_action_data[0]].clear()
                self.resolve_locations()
        elif self.current_type_of_action == 4:
            location = self.locations[self.current_action_data[0]]
            if isinstance(location, Card):
                self.buy_card(location)
                self.apply_card_effect(location)
                self.current_action_data = [0,0,0,0]
                self.resolve_locations()
            else:
                self.buy_building(self.current_action_data[0], action)
                self.current_action_data = [0,0,0,0]
                self.resolve_locations()
        elif self.current_type_of_action == 5:
            self.current_player.get_reward(action[0])
            self.current_action_data.remove(action[0])
            self.next_player()
            if self.current_action_data:
                self.resolve_locations()
        elif self.current_type_of_action == 6:
        # Choose 2 resources: action = [resource1, resource2, 0, 0, 0, 0, 0]
            self.current_player.get_resources(action[0], 1)
            self.current_player.get_resources(action[1], 1)
            self.resolve_locations()
        reward = self.calculate_reward(current_score, player_active.get_score(), player_active)
        return reward, self.game_end, player_active.get_vp()
    
    def calculate_reward(self, past_score, current_score, player_active):
        """
        Improved reward function with dense shaping signals.

        Key principles:
        1. VP is the ultimate goal - weight it heavily
        2. Penalize starvation risk based on worker/food imbalance
        3. Reward sustainable growth (wheat before workers)
        4. Small bonuses for resource accumulation (enables future purchases)
        """

        # ===== PRIMARY: Victory Point Change =====
        vp_delta = current_score[3] - past_score[3]
        reward = vp_delta * 2.0  # Amplify VP signal - this is what matters

        # ===== STARVATION RISK PENALTY =====
        food = current_score[0][2]
        wheat = current_score[1] - past_score[1]
        workers = current_score[2] - current_score[2]

        # Sustainable food = wheat covers workers, so only need buffer for variance
        food_needed_next_round = max(0, workers - wheat)
        food_surplus = food - food_needed_next_round

        if food_surplus < 0:
            # Imminent starvation - harsh penalty
            reward -= 10
        elif food_surplus < 3:
            # Risky - mild penalty  
            reward -= 2

        # ===== WORKER/WHEAT IMBALANCE PENALTY =====
        # Penalize having more workers than wheat can sustain
        # This teaches: get wheat BEFORE getting workers
        worker_wheat_gap = workers - wheat
        if worker_wheat_gap > 6:
            reward -= (worker_wheat_gap - 6) * 1.5  # -1.5 per excess worker

        # ===== REWARD FOR STARVATION IMMUNITY =====
        # Bonus if wheat >= workers (never need to worry about food)
        if wheat >= workers:
            reward += 1.0

        
        # ===== END OF GAME BONUS/PENALTY =====
        if self.game_end:
            final_vp = current_score[3]

            res = sum(r for r in current_score[0])

            # Tiered bonuses for good scores
            if final_vp >= 0:
                reward += 100
            elif final_vp >= -30:
                reward += 40
            elif final_vp >= -60:
                reward += 15
            elif final_vp >= -100:
                reward += 5

            # Light penalty for wasted resources at end
            reward -= (res) * 0.05

        return reward


    def check_if_any_uncollectedhumans_left(self):
        return any(loc.is_occupied(self.current_player_idx) for loc in self.locations if loc is not None)
    # TODO: Implement missing methods
    # - reset(): Reset game state for next episode
    # - get_random_legal_action(): Better random move selection

    def reset(self):
        self.start_game()
