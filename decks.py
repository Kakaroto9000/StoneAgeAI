"""
Deck definitions for Stone Age board game.

This module contains the official 36 civilization cards and 28 building tiles
from the Stone Age board game, ready to be imported into game.py.

1-transport
2-pottery
3-writing
4-healing
5-weaving
6-art
7-music
8-time


Usage:
    from decks import create_card_deck, create_building_decks
    
    cards_in_deck = create_card_deck()
    buildings_in_deck = create_building_decks()
"""

import random
from card import Card
from building import CertainBuilding, FlexBuilding


def create_card_deck(shuffle: bool = True) -> list[Card]:
    """
    Create the official Stone Age 36 civilization card deck.
    
    Card costs are 1-4 based on position (rightmost=1, leftmost=4).
    
    Args:
        shuffle: Whether to shuffle the deck (default True)
    
            1: 0,      # VP per tool value
            2: 0,  # VP per building owned
            3: 0,    # VP per worker
            4: 0,      # VP per wheat
    Returns:
        List of 36 Card objects
    """
    cards = [
        # === DICE ROLL CARDS (10 cards) ===
        # Each player picks a die: 1=wood, 2=brick/clay, 3=stone, 4=gold, 5=tool, 6=wheat
        Card("dice_roll", cost=0, multiplier=32),   # pottery
        Card("dice_roll", cost=0, multiplier=21),   # 1 hut builder  
        Card("dice_roll", cost=0, multiplier=22),   # 2 hut builders
        Card("dice_roll", cost=0, multiplier=41),   # writing
        Card("dice_roll", cost=0, multiplier=42),   # 2 tool makers
        Card("dice_roll", cost=0, painting=1),   # 1 farmer
        Card("dice_roll", cost=0, painting=8),   # 2 farmers
        Card("dice_roll", cost=0, painting=2),   # time
        Card("dice_roll", cost=0, painting=3),   # transport
        #Card("dice_roll", cost=0, painting=2),   # medicine
        
        # === FOOD CARDS (7 cards) ===
        Card("add_resource", cost=1, data={"resources": 2, "amount": 7}, painting=2),   # 7 food
        Card("add_resource", cost=1, data={"resources": 2, "amount": 2}, multiplier=22),   # 2 food
        Card("add_resource", cost=2, data={"resources": 2, "amount": 4}, multiplier=21),   # 4 food
        Card("add_resource", cost=2, data={"resources": 2, "amount": 5}, painting=4),   # 5 food
        Card("add_resource", cost=3, data={"resources": 2, "amount": 3}, painting=5),   # 3 food
        Card("add_resource", cost=3, data={"resources": 2, "amount": 1}, painting=5),   # 1 food
        Card("add_resource", cost=4, data={"resources": 2, "amount": 3}, multiplier=42),   # 3 food
        
        # === RESOURCE CARDS (5 cards) ===
        Card("add_resource", cost=1, data={"resources": 4, "amount": 1}, multiplier=41),   # 1 stone
        Card("add_resource", cost=2, data={"resources": 4, "amount": 2}, painting=1),   # 2 stones
        Card("add_resource", cost=2, data={"resources": 4, "amount": 1}, multiplier=31),   # 1 stone
        Card("add_resource", cost=3, data={"resources": 6, "amount": 1}, multiplier=31),   # 1 gold
        Card("add_resource", cost=3, data={"resources": 5, "amount": 1}, multiplier=32),   # 1 brick
        
        # === RESOURCES WITH DICE (3 cards) ===
        Card("resources_with_dice", cost=2, data={"resource_type": 6}, painting=6),     # gold
        Card("resources_with_dice", cost=3, data={"resource_type": 3}, multiplier=32),     # wood
        Card("resources_with_dice", cost=3, data={"resource_type": 4}, multiplier=31),     # stone
        
        # === VICTORY POINTS (3 cards) ===
        Card("add_vp", cost=2, data={"vp": 3}, multiplier=23),   # 3 VP
        Card("add_vp", cost=3, data={"vp": 3}, painting=7),   # 3 VP
        Card("add_vp", cost=4, data={"vp": 3}, painting=7),   # 3 VP
        
        # === TOOL CARD (1 card) ===
        Card("add_tool", cost=2, painting=6),   # +1 tool
        
        # === WHEAT/FOOD PRODUCTION CARDS (2 cards) ===
        Card("add_wheat", cost=2, multiplier=41),  # +1 food production
        Card("add_wheat", cost=3, painting=8),  # +1 food production
        
        # === DRAW CARD (1 card) ===
        Card("draw_card", cost=3, painting=3),  # draw extra card
        
        # === ONE-USE TOOL CARDS (3 cards) ===
        Card("one_use_tool", cost=1, data={"tool_value": 4}, multiplier=11),  # 4 tools
        Card("one_use_tool", cost=2, data={"tool_value": 3}, multiplier=11),  # 3 tools  
        Card("one_use_tool", cost=3, data={"tool_value": 2}, multiplier=12),  # 2 tools
        
        # === ANY 2 RESOURCES (1 card) ===
        Card("any_2_resources", cost=2, painting=4),  # 2 resources of choice
    ]
    
    if shuffle:
        random.shuffle(cards)
    
    return cards


def create_building_decks() -> dict[int, list]:
    """
    Create the official Stone Age 28 building tile decks.
    
    Buildings are split into 4 stacks of 7 tiles each.
    Resources: 3=wood, 4=stone, 5=clay/brick, 6=gold
    
    Returns:
        Dict mapping stack index (0-3) to list of Building objects
    """
    return {
        0: [
            # 2 same + 1 different type buildings
            CertainBuilding(resources=[3, 3, 5]),      # 2 wood + 1 brick = 10 pts
            CertainBuilding(resources=[3, 3, 4]),      # 2 wood + 1 stone = 11 pts
            CertainBuilding(resources=[3, 5, 5]),      # 1 wood + 2 brick = 11 pts
            # 3 different kinds
            CertainBuilding(resources=[3, 5, 4]),      # wood + brick + stone = 12 pts
            CertainBuilding(resources=[3, 5, 6]),      # wood + brick + gold = 13 pts
            # Flex buildings - 4 resources  # 4 resources, 1 kind
            FlexBuilding(resources_require_count=4, variety=2),  # 4 resources, 2 kinds
        ],
        1: [
            CertainBuilding(resources=[3, 3, 6]),      # 2 wood + 1 gold = 12 pts
            CertainBuilding(resources=[3, 4, 4]),      # 1 wood + 2 stone = 13 pts
            CertainBuilding(resources=[5, 5, 4]),      # 2 brick + 1 stone = 13 pts
            # 3 different
            CertainBuilding(resources=[3, 4, 6]),      # wood + stone + gold = 14 pts
            CertainBuilding(resources=[5, 4, 6]),      # brick + stone + gold = 15 pts
            # Flex buildings - 4 resources  
            FlexBuilding(resources_require_count=4, variety=3),  # 4 resources, 3 kinds
            FlexBuilding(resources_require_count=4, variety=4),  # 4 resources, 4 kinds
        ],
        2: [
            CertainBuilding(resources=[5, 5, 6]),      # 2 brick + 1 gold = 14 pts
            CertainBuilding(resources=[5, 4, 4]),      # 1 brick + 2 stone = 14 pts
            CertainBuilding(resources=[4, 4, 6]),      # 2 stone + 1 gold = 16 pts
            # Flex buildings - 5 resources
            FlexBuilding(resources_require_count=5, variety=1),  # 5 resources, 1 kind
            FlexBuilding(resources_require_count=5, variety=2),  # 5 resources, 2 kinds  # 5 resources, 3 kinds
            FlexBuilding(resources_require_count=5, variety=4),  # 5 resources, 4 kinds
        ],
        3: [
            # 1-7 resources any kind (3 cards in official game)
            FlexBuilding(resources_require_count=5, variety=3),  # 1-7 resources
            FlexBuilding(resources_require_count=7, variety=None),  # 1-7 resources
            FlexBuilding(resources_require_count=4, variety=1),  # 1-7 resources
            # Fill rest with 3-different buildings
    # wood + stone + clay
            CertainBuilding(resources=[4, 5, 6]),      # stone + clay + gold
            CertainBuilding(resources=[3, 4, 6]),      # wood + stone + gold      # wood + clay + gold
        ],
    }


def create_starting_cards() -> list[Card]:
    """
    Create the 4 starting cards that go on the board at game start.
    
    Returns:
        List of 4 Card objects for initial board setup
    """
    return [
        Card("add_resource", cost=1, data={"resources": 2, "amount": 5}, painting=1),
        Card("add_resource", cost=2, data={"resources": 2, "amount": 4}, painting=1),
        Card("dice_roll", cost=3, painting=1),
        Card("add_tool", cost=4, painting=2),
    ]


def create_starting_buildings() -> list:
    """
    Create the 4 starting buildings that go on the board at game start.
    
    Returns:
        List of 4 Building objects for initial board setup
    """
    return [
        CertainBuilding(resources=[3, 3, 5]),          # 2 wood + 1 brick
        FlexBuilding(resources_require_count=4, variety=2),  # 4 resources, 2 kinds
        CertainBuilding(resources=[3, 4, 5]),          # wood + stone + clay
        CertainBuilding(resources=[4, 5, 6]),          # stone + clay + gold
    ]