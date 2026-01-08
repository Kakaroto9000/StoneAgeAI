from typing import List, Dict, Optional, Any
import random

from area import Area
from player import Player
from map import GameMap
from building import Building
from card import Card
from utility import Utility

class Game:
    """Minimal StoneAge game skeleton.

    This file provides the high-level orchestration and stub methods
    to implement game mechanics incrementally.
    """

    def __init__(
        self,
        players: List[Player],
        game_map: Optional[Any] = None,
        buildings: Optional[List[Any]] = None,
        cards: Optional[List[Any]] = None,
    ) -> None:
        self.players: List[Player] = players
        self.map = game_map
        self.buildings = buildings or []
        self.cards = cards or []
        self.round = 0
        self.current_player_idx = 0
        # map of location_id -> list of (player, worker_count)
        self.occupancy: List[Optional[Any]] = [
            Utility("Farm", 1),
            Utility("House", 2),
            Utility("ToolShop", 1),
            Area(40, 2),
            Area(7, 3),
            Area(7, 4),
            Area(7, 5),
            Area(7, 6),
            Card("Card1", cost=1),
            Card("Card2", cost=2),
            Card("Card3", cost=3),
            Card("Card4", cost=4),
            Building("Hut1", cost=(3, 2, 1)),
            Building("Hut2", cost=(4, 3, 2)),
            Building("Hut3", cost=(3, 4, 3, 2)),
            Building("Hut4", cost=(6, 5, 4, 3)),
        ]

    def start_game(self, seed: Optional[int] = None) -> None:
        """Prepare and run the game rounds."""
        if seed is not None:
            random.seed(seed)
        for p in self.players:
            # ensure each player has available workers
            if hasattr(p, "available_workers"):
                p.available_workers = 5

    def run_game(self) -> None:
        """Run the game for a fixed number of rounds."""
        while self.game_not_ended():
            self.run_round()
    
    def game_not_ended(self) -> bool:
        """Determine if the game should continue.

        """
        if any(building for building in self.buildings if building is None):
            return False
        if any(card for card in self.cards if card is None):
            return False
        return True

    def run_round(self) -> None:
        """High-level flow for a single round:

        - placement phase (players call `place_worker`)
        - resolution phase (`resolve_locations`)
        - feeding (`feed_players`)
        - cleanup/replenish
        """
        self.round += 1
        # Reset occupancy
        for area in self.occupancy:
            area.clear()
        while self.round_not_over():
            for player in self.players:
                if player.available_workers > 0:
                    action = player.decide_action(self)
                    self.execute_an_action(action, player)
                    

        self.resolve_locations()
        # Feeding phase
        self.feed_players()
        # Cleanup/replenish phase would go here

    def execute_an_action(self, action: Any, player: Any) -> None:
        """Execute a player's chosen action.

        This is a stub; actual implementation would parse `action`
        and call appropriate methods like `place_worker`, `build`, etc.
        """
        if self.occupancy[action['location_id']].can_place(action['count']):
            self.place_worker(player, action['location_id'], action['count'])

    def round_not_over(self) -> bool:
        """Determine if the current round is still ongoing.

        This is a stub; actual implementation would check if all players
        have placed their workers.
        """
        return any(p.available_workers > 0 for p in self.players)

    def place_worker(self, player: Any, location_id: Any, count: int = 1):
        """Attempt to place `count` workers for `player` at `location_id`.
        """
        # Validate inputs and location capacity using `self.map` if available.
        # Update `self.occupancy` and `player.available_workers` accordingly.
        self.occupancy[location_id].place(player, count)
        player.available_workers -= count

    def resolve_locations(self) -> None:
        """Resolve yields/effects for all occupied locations.

        Should iterate through locations in the proper order and call
        map/location resolver methods to grant resources, allow building,
        and apply dice-based outcomes.
        """
        for location in self.occupancy:
            if location.is_occupied():
                if isinstance(location, Utility):
                    player_own = location.player_occupy()
                    if location.name() == "Farm":
                        self.players[player_own].gain_wheat()
                    elif location.name() == "House":
                        self.players[player_own].gain_worker()
                    elif location.name() == "Tools":
                        self.players[player_own].gain_tool()
                elif isinstance(location, (Card, Building)):
                    player_own = location.player_occupy()
                    if self.players[player_own].decide_if_buy():
                        self.player_get_card(location)
                else:
                    for player, count in location.occupants:
                        dice_results = self.roll_dice(count)
                        self.players[player].get_resources(location.resource_type, dice_results)

    def roll_dice(self, n: int = 1) -> int:
        """Roll `n` six-sided dice and return results."""
        return sum(random.randint(1, 6) for _ in range(n))
    
    def roll_dices(self, n: int = 1) -> List[int]:
        """Roll `n` six-sided dice and return results as a list."""
        return [random.randint(1, 6) for _ in range(n)]

    def player_get_card(self, card: Card) -> bool:
        """Player attempts to buy/build a building by id.

        Returns True on success.
        """
        player = card.occupant
        effect = card.immediate_effect()
        self.apply_card_effect(self.players[player], effect)
        player.get_card(card)
        return True
    
    def next_player(self) -> int:
        """Advance to the next player and return their index."""
        self.current_player_idx = (self.current_player_idx + 1) % len(self.players)
        return self.current_player_idx

    def apply_card_effect(self, player: Player, effect: Dict[str, Any]) -> None:
        """Apply the effect of a card to a player."""
        effect_type = effect.get("type")
        if effect_type == "add_resource":
            player.resources[effect["resource"]] += effect["amount"]
        elif effect_type == "dice_roll":
            # Placeholder: handle dice roll with choices
            dices = self.roll_dices(len(self.players))
            self.players[self.current_player_idx].choose_reward(dices)
            for _ in range(len(self.players)-1):
                self.players[self.next_player()].choose_reward(dices)
            self.next_player() 
        elif effect_type == "resources_with_dice":
            dice_sum = sum(random.randint(1, 6) for _ in range(2))
            resource_type = effect["resource_type"]
            dice_sum = player.decide_to_use_tool(dice_sum, resource_type)
            amount = dice_sum // resource_type
            player.resources[resource_type] += amount
        elif effect_type == "add_vp":
            player.vp += effect["points"]
        elif effect_type == "add_tool":
            player.get_tool()
        elif effect_type == "add_wheat":
            player.get_wheat(1)
        elif effect_type == "civilization":
            # Placeholder
            player.get_card(self.draw_card())
        elif effect_type == "one_use_tool":
            # Mark as available
            player.get_one_use_tool(effect["tool_value"])
        elif effect_type == "any_2_resources":
            # Placeholder
            player.choose_resources(2)

    def feed_players(self) -> None:
        """Charge food for each player and apply penalties on shortages."""
        for num, p in enumerate(self.players):
            score_change = p.feed()
            self.p_points[num] += score_change

    def serialize(self) -> Dict[str, Any]:
        """Return a simple serializable snapshot of the game state."""
        return {
            "round": self.round,
            "players": [getattr(p, "name", str(p)) for p in self.players],
            "occupancy": {str(k): v for k, v in self.occupancy.items()},
        }

    def draw_card(self) -> Card:
        """Draw a card from the deck."""
        if self.cards:
            return self.cards.pop(0)
        return None
