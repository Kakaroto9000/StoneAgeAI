"""
Card module for Stone Age board game cards.

This module defines the Card class, which represents purchasable cards that
provide special effects and victory point bonuses. Cards have immediate effects
(triggered when purchased) and end-game effects (scored at game end).

Card types include resource bonuses, dice roll selections, tools, wheat, victory
points, and various special abilities.

Classes:
    Card: Purchasable card with immediate and end-game effects.
"""

from typing import Dict, Any, List
from area import Area

# Mapping of card type names to numeric identifiers
# Used for state representation (neural network input)
CARD_TYPE_NUMBERS = {
    "add_resource": 1,           # Gain resources
    "dice_roll": 2,              # Roll dice and choose reward
    "resources_with_dice": 3,    # Get resources based on dice roll
    "add_vp": 4,                 # Immediate victory points
    "add_tool": 5,               # Gain a tool
    "add_wheat": 6,              # Gain wheat
    "draw_card": 7,              # Draw another card
    "one_use_tool": 8,           # Gain a single-use tool
    "any_2_resources": 9         # Choose 2 resources
}


class Card(Area):
    """
    A purchasable card that provides immediate and end-game effects.
    
    Cards are special items players can buy at a cost. They provide immediate
    benefits (resources, tools, etc.) when purchased, and may also contribute
    victory points at game end based on other card collections.
    
    Inherits from Area to track which player owns it (capacity always 1).
    
    Attributes:
        cost (int): Resource cost to purchase this card.
        card_id (int): Numeric ID of the card type (from CARD_TYPE_NUMBERS).
        card_type (str): String identifier of card type (e.g., "add_resource").
        data (Dict[str, int]): Card-specific data (resource types, amounts, etc.).
        painting (int): End-game scoring value based on collections.
        multiplier (int): Multiplier for end-game scoring calculations.
    """
    
    def __init__(self, card_type: str, cost: int, data: Dict[str, int] = None, 
                 painting: int = None, multiplier: str = None) -> None:
        """
        Initialize a Card with type, cost, and effects.
        
        Args:
            card_type (str): Type of card (key from CARD_TYPE_NUMBERS).
                            Must be one of: add_resource, dice_roll, 
                            resources_with_dice, add_vp, add_tool, add_wheat,
                            draw_card, one_use_tool, any_2_resources.
            cost (int): Resource cost to purchase this card.
            data (Dict[str, int], optional): Card-specific data. Contents depend
                                            on card_type. Defaults to None.
            painting (int, optional): End-game victory point value. Defaults to None.
            multiplier (int, optional): Multiplier for end-game scoring. 
                                       Defaults to None.
        """
        super().__init__(1)  # Cards have capacity 1 (one owner per card)
        self.cost = cost
        self.card_id = CARD_TYPE_NUMBERS[card_type]
        self.card_type = card_type
        self.data = data if data is not None else {}
        self.painting = painting
        self.multiplier = multiplier
    
    @property
    def card_type_num(self) -> int:
        """
        Get the numeric representation of the card type.
        
        Used for neural network input representation, since networks work
        better with numeric inputs than strings.
        
        Returns:
            int: Numeric ID for this card type (1-9), or 0 if type is unknown.
        """
        return CARD_TYPE_NUMBERS.get(self.card_type, 0)

    def immediate_effect(self) -> list[int]:
        """
        Return the immediate effect triggered when this card is purchased.
        
        Different card types have different immediate effects:
        - add_resource: Return [resource_type, amount]
        - resources_with_dice: Return [resource_type]
        - one_use_tool: Return [tool_value]
        - add_vp: Return [vp_amount]
        
        Returns:
            list[int]: Effect parameters as integers. Contents depend on card_type.
        """
        if self.card_type == "add_resource":
            return [self.data.get("resources", 2), self.data.get("amount", 1)]
        elif self.card_type == "resources_with_dice":
            return [self.data.get("resource_type", 2)]
        elif self.card_type == "one_use_tool":
            return [self.data.get("tool_value", 1)]
        elif self.card_type == "add_vp":
            return [self.data.get("add_vp", 3)]
        
        # Unknown card type or card with no immediate effect
        return []

    def end_game_effect(self) -> int:
        """
        Calculate the end-game victory point contribution from this card.
        
        This is the "painting" value - how many points this card contributes
        at game end. Some cards provide victory points based on how many
        cards of that type a player owns.
        
        Returns:
            int: Victory points from this card at game end (or 0 if None).
        """
        return self.painting if self.painting is not None else self.multiplier
    
    def name(self) -> str:
        """
        Return a descriptive name for this card.
        
        Returns:
            str: String description including card type, data, and end-game value.
        """
        return f"{self.card_type} {self.data} {self.end_game_effect()}"
    
    def is_able_to_buy(self, player_resources: Dict[int, int]) -> bool:
        """
        Check if a player has enough resources to purchase this card.
        
        A player can buy a card if their total resources are at least equal
        to the card's cost. This is simpler than buildings, which require
        specific resource types.
        
        Args:
            player_resources (Dict[int, int]): Player's resource inventory.
            Keys are resource types (2-6).
        
        Returns:
            bool: True if player has >= cost resources total, False otherwise.
        """
        # Sum all resources the player has
        total_resources = sum(v for key,v in player_resources.items() if key != 2)
        
        # Can buy if total >= cost
        return self.cost <= total_resources