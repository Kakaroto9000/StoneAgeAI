from typing import Dict, Any, List
from area import Area
# Number table for card types
CARD_TYPE_NUMBERS = {
    "food": 1,
    "resource": 2,
    "dice_roll": 3,
    "resources_with_dice": 4,
    "victory_points": 5,
    "extra_tool": 6,
    "agriculture": 7,
    "civilization": 8,
    "one_use_tool": 9,
    "any_2_resources": 10
}

class Card(Area):
    def __init__(self, card_type: str, cost: int, data: Dict[str, int] = None, painting: int = None, multiplier: int = None) -> None:
        super().__init__(1)
        self.cost = cost
        self.card_type = card_type  # e.g., "food", "resource", "dice_roll", "victory_points", etc.
        self.data = data  # Dictionary with card-specific data
        self.painting = painting
        self.multiplier = multiplier
    
    @property
    def card_type_num(self) -> int:
        """Get the numeric representation of the card type."""
        return CARD_TYPE_NUMBERS.get(self.card_type, 0)  # 0 for unknown types

    def immediate_effect(self) -> list[int]:
        """Return a description of the card's immediate effect."""
        if self.card_type == "add_resource":
            return [self.data.get("resources", 2), self.data.get("amount", 1)]
        elif self.card_type == "resources_with_dice":
            return [self.data.get("resource_type", 2)]
        elif self.card_type == "one_use_tool":
            return [self.data.get("tool_value", 1)]
        elif self.card_type == "gain_vp":
            return [self.data.get("gain_vp", 3)]

    def end_game_effect(self) -> int:
        """Calculate the end-game effect for scoring."""
        if self.card_type == "civilization":
            return self.multiplier if self.multiplier else self.painting
        return 0
    
    def name(self) -> str:
        return f"{self.card_type} {self.data} {self.end_game_effect()}"
    
    def is_able_to_buy(self, player_resources: Dict[int, int]) -> bool:
        """Check if a player has enough resources to buy this building.

        """
        # Get the resource counts, sorted in descending order
        resources = sum(player_resources.values())
        # Sum the top 'variety' counts (or all if variety is None or more than available)
        return self.cost<= resources
