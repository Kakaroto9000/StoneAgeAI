from typing import List, Dict, Optional, Any
import random

from area import Gathering, Area
from player import Player
from building import CertainBuilding, FlexBuilding, Building
from card import Card
from utility import Utility

class Game:
    """Minimal StoneAge game skeleton.

    This file provides the high-level orchestration and stub methods
    to implement game mechanics incrementally.
    """

    def __init__(
        self,
    ) -> None:
        self.players: List[Player] = (Player(), Player(), Player(), Player())
        self.round = 0
        self.current_player_idx = 0
        # map of location_id -> list of (player, worker_count)
        self.locations: List[Optional[Any]] = [
            Utility("Farm", 1),
            Utility("House", 2),
            Utility("ToolShop", 1),
            Gathering(40, 2),
            Gathering(7, 3),
            Gathering(7, 4),
            Gathering(7, 5),
            Gathering(7, 6),
            Card("resource", cost=1),
            Card("resource", cost=2),
            Card("resource", cost=3),
            Card(cost = 4,card_type ="resource", data=[2,7]),
            CertainBuilding(resources=(6,6,3)),
            FlexBuilding(resources_require_count=5, variety=2),
            CertainBuilding(resources=(3, 4, 3)),
            CertainBuilding(resources=(6, 5, 4)),
        ]
        self.cards_in_deck: List[Card] = []
        self.buildings_in_deck: Dict[int: List[Building]] = {}

    @property
    def current_player(self) -> Player:
        """Get the current player."""
        return self.players[self.current_player_idx]

    def start_game(self, seed: Optional[int] = None) -> None:
        """Prepare and run the game rounds."""
        if seed is not None:
            random.seed(seed)
        for p in self.players:
            p.total_workers = 5
            p.available_workers = 5
        print(f"Game started with {len(self.players)} players")

    def run_game(self) -> None:
        """Run the game for a fixed number of rounds."""
        while self.game_not_ended():
            self.run_round()

    def game_not_ended(self) -> bool:
        """Determine if the game should continue.

        """
        return len(self.locations) == 16

    def run_round(self) -> None:
        """High-level flow for a single round:

        - placement phase (players call `place_worker`)
        - resolution phase (`resolve_locations`)
        - feeding (`feed_players`)
        - cleanup/replenish
        """
        self.round += 1
        print(f"== Starting Round {self.round} ==")
        # Reset locations
        for area in self.locations:
            area.clear()
        while self.round_not_over():
            if self.current_player.available_workers > 0:
                avaliable_actions = self.get_avaliable_actions()
                action = self.current_player.decide_action(avaliable_actions)
                self.execute_an_action(action)
            self.next_player()

        # Resolution phase

        for _ in range(len(self.players)):
            self.resolve_locations()
        # Feeding phase
        self.feed_players()
        self.refresh_humans()
        # Cleanup/replenish phase would go here
        self.get_new_buildings_and_cards()

    def get_avaliable_actions(self):
        avaliable_actions = []
        for index, location in enumerate(self.locations):
            if location.can_place():
                avaliable_actions.append([index, location.avaliable_space()])
        return avaliable_actions

    def execute_an_action(self, action: Any) -> None:
        """Execute a player's chosen action.

        This is a stub; actual implementation would parse `action`
        and call appropriate methods like `place_worker`, `build`, etc.
        """
        if self.locations[action[0]].can_place(action[1]):
            print(f"Player {self.current_player_idx} executes action {action}")
            self.place_worker(self.current_player, action[0], action[1])

    def round_not_over(self) -> bool:
        """Determine if the current round is still ongoing.

        This is a stub; actual implementation would check if all players
        have placed their workers.
        """
        return any(p.available_workers > 0 for p in self.players)

    def place_worker(self, location_id: Any, count: int = 1):
        """Attempt to place `count` workers for `player` at `location_id`.
        """
        # Validate inputs and location capacity using `self.map` if available.
        # Update `self.locations` and `player.available_workers` accordingly.
        print(f"Player {self.current_player_idx} places {count} worker(s) at location {location_id}")
        self.locations[location_id].place(self.current_player, count)
        self.current_player.available_workers -= count

    def resolve_locations(self) -> None:
        """Resolve yields/effects for all occupied locations.

        Should iterate through locations in the proper order and call
        map/location resolver methods to grant resources, allow building,
        and apply dice-based outcomes.
        """
        print(f"Resolving locations for player {self.current_player_idx}")
        for location in self.locations:
            if location.is_occupied() == self.current_player_idx:
                if isinstance(location, Utility):
                    print(f"  Utility resolved: {location.name()}")
                    if location.name() == "Farm":
                        self.current_player().gain_wheat()
                    elif location.name() == "House":
                        self.current_player().gain_worker()
                    elif location.name() == "Tools":
                        self.current_player().gain_tool()
                elif isinstance(location, (Card, Building)):
                    print(f"  Offer to buy at location: {location}")
                    if self.current_player().decide_if_buy(location):
                        print(f"  Player {self.current_player_idx} buys {location}")
                        self.player_get_card(location)
                else:
                    count = location.occupants[self.current_player_idx]
                    dice_results = self.roll_dices(count)
                    print(f"  Player {self.current_player_idx} rolled {dice_results} on {location}")
                    self.current_player().get_resource_with_die(location.resource_type, dice_results)
        self.next_player()

    def roll_dices(self, n: int = 1) -> int:
        """Roll `n` six-sided dice and return a sum."""
        return sum(random.randint(1, 6) for _ in range(n))

    def roll_dicess_separate(self, n: int = 1) -> List[int]:
        """Roll `n` six-sided dice and return results as a list."""
        return [random.randint(1, 6) for _ in range(n)]

    def player_get_card(self, card: Card) -> bool:
        """Player buys a card and removes it from the display.

        Returns True on success.
        """
        # Find card index in display
        card_idx = self.cards.index(card) if card in self.cards else -1

        print(f"Player {self.current_player_idx} acquiring card: {card}")
        self.apply_card_effect(self.current_player, card)
        self.current_player.get_card(card)

        # Mark card as bought (None) so it can be shifted out later
        if card_idx >= 0:
            self.cards[card_idx] = None

        return True

    def next_player(self) -> int:
        """Advance to the next player and return their index."""
        self.current_player_idx = (self.current_player_idx + 1) % len(self.players)
        print(f"Next player: {self.current_player_idx}")
        return self.current_player_idx

    def apply_card_effect(self, card: Card) -> None:
        """Apply the effect of a card to a player."""
        effect_type = card.card_type
        effect = card.immediate_effect()
        if effect_type == "add_resource":
            resource_type = card.data[0]
            resource_amount = card.data[1]
            print(f"Applying card effect add_resource: +{resource_amount} of {resource_type} to player {self.current_player_idx}")
            self.current_player.get_resources(resource_type, resource_amount)
        elif effect_type == "dice_roll":
            # Placeholder: handle dice roll with choices
            dices = self.roll_dicess_separate(len(self.players))
            self.current_player.choose_reward_and_apply(dices)
            for _ in range(len(self.players)-1):
                self.next_player().choose_reward_and_apply(dices)
            self.next_player()
        elif effect_type == "resources_with_dice":
            dice_sum = sum(random.randint(1, 6) for _ in range(2))
            resource_type = card.data[0]
            dice_sum = self.current_player.decide_to_use_tool(dice_sum, resource_type)
            amount = dice_sum // resource_type
            self.current_player.resources[resource_type] += amount
        elif effect_type == "add_vp":
            self.current_player.vp += 3 #default value for vp
        elif effect_type == "add_tool":
            self.current_player.get_tool()
        elif effect_type == "add_wheat":
            self.current_player.get_wheat(1)
        elif effect_type == "civilization":
            # Placeholder
            self.current_player.get_card(self.draw_card())
        elif effect_type == "one_use_tool":
            # Mark as available
            self.current_player.get_one_use_tool(card.data["tool_value"])
        elif effect_type == "any_2_resources":
            # Placeholder
            self.current_player.choose_resources(2)
            self.current_player.get_resources(2,2)

    def feed_players(self) -> None:
        """Charge food for each player and apply penalties on shortages."""
        for player in self.players:
            player.feed()

    def get_new_buildings_and_cards(self) -> None:
        """Replenish buildings and cards as needed."""
        # Handle card replenishment with shifting
        self.replenish_buildings()
        self.replenish_cards()

    def replenish_buildings(self) -> None:
        """
        replenish building from each deck respectively
        """
        for i, building in enumerate(self.buildings):
            if building is None:
                new_building = self.draw_building(i)
                if new_building:
                    self.buildings[i] = new_building

    def replenish_cards(self) -> None:
        """Remove bought cards and shift remaining cards, then draw new ones."""
        # Find all None positions (bought cards)
        bought_indices = [i for i, card in enumerate(self.cards) if card is None]

        # Shift remaining cards to fill gaps from left to right
        if bought_indices:
            # Remove all None values
            self.cards = [card for card in self.cards if card is not None]
            # Draw new cards to fill the missing slots
            for _ in bought_indices:
                new_card = self.draw_card()
                if new_card:
                    self.cards.append(new_card)

    def refresh_humans(self) -> None:
        """Refresh human players' available workers at round end."""
        for p in self.players:
            p.available_workers = p.total_workers

    def draw_card(self) -> Card:
        """Draw a card from the deck."""
        if self.cards:
            card = self.cards.pop(0)
            print(f"Drew card: {card}")
            return card
        print("No card to draw")
        return None
    
    def draw_building(self, location_id: int) -> Building:
        """Draw a building from the deck for a specific location."""
        if location_id in self.buildings_in_deck and self.buildings_in_deck[location_id]:
            b = self.buildings_in_deck[location_id].pop(0)
            print(f"Drew building for location {location_id}: {b}")
            return b
        print(f"No building to draw for location {location_id}")
        return None

game = Game()
game.run_game()
