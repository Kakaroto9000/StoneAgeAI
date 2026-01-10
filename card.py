from typing import Dict, Any
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
    def __init__(self, cost: int, card_type: str, data: list[int] = None, painting: int = None, multiplier: int = None) -> None:
        super.__init__(1)
        self.cost = cost
        self.card_type = card_type  # e.g., "food", "resource", "dice_roll", "victory_points", etc.
        self.data = data  # Dictionary with card-specific data
        self.painting = painting
        self.multiplier = multiplier
    
    @property
    def card_type_num(self) -> int:
        """Get the numeric representation of the card type."""
        return CARD_TYPE_NUMBERS.get(self.card_type, 0)  # 0 for unknown types

    def immediate_effect(self) -> Dict[str, Any]:
        """Return a description of the card's immediate effect."""
        if self.card_type == "resource":
            return {"type": "add_resources", "resources": self.data.get("resources", 2), "ammount": self.data.get("amount", 1)}
        elif self.card_type == "resources_with_dice":
            return {"type": "resources_with_dice", "resource_type": self.data.get("resource_type", 2),}
        elif self.card_type == "one_use_tool":
            return {"type": "one_use_tool", "tool_value": self.data.get("tool_value", 0)}
        return {"type": self.card_type}

    def end_game_effect(self) -> int:
        """Calculate the end-game effect for scoring."""
        if self.card_type == "civilization":
            return self.multiplier if self.multiplier else self.painting
        return 0
    