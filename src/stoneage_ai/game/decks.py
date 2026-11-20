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
    from stoneage_ai.game.decks import create_card_deck, create_building_decks
    
    cards_in_deck = create_card_deck()
    buildings_in_deck = create_building_decks()
"""

import random
from .card import Card
from .building import CertainBuilding, FlexBuilding


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
        Card("add_resource", cost=1, data={"resources": 2, "amount": 4}, multiplier=21),   # 4 food
        Card("add_resource", cost=1, data={"resources": 2, "amount": 5}, painting=4),   # 5 food
        Card("add_resource", cost=1, data={"resources": 2, "amount": 3}, painting=5),   # 3 food
        Card("add_resource", cost=1, data={"resources": 2, "amount": 1}, painting=5),   # 1 food
        Card("add_resource", cost=1, data={"resources": 2, "amount": 3}, multiplier=42),   # 3 food

        # === RESOURCE CARDS (5 cards) ===
        Card("add_resource", cost=1, data={"resources": 4, "amount": 1}, multiplier=41),   # 1 stone
        Card("add_resource", cost=1, data={"resources": 4, "amount": 2}, painting=1),   # 2 stones
        Card("add_resource", cost=1, data={"resources": 4, "amount": 1}, multiplier=31),   # 1 stone
        Card("add_resource", cost=1, data={"resources": 6, "amount": 1}, multiplier=31),   # 1 gold
        Card("add_resource", cost=1, data={"resources": 5, "amount": 1}, multiplier=32),   # 1 brick
        
        # === RESOURCES WITH DICE (3 cards) ===
        Card("resources_with_dice", cost=1, data={"resource_type": 6}, painting=6),     # gold
        Card("resources_with_dice", cost=1, data={"resource_type": 3}, multiplier=32),     # wood
        Card("resources_with_dice", cost=1, data={"resource_type": 4}, multiplier=31),     # stone
        
        # === VICTORY POINTS (3 cards) ===
        Card("add_vp", cost=1, data={"vp": 3}, multiplier=23),   # 3 VP
        Card("add_vp", cost=1, data={"vp": 3}, painting=7),   # 3 VP
        Card("add_vp", cost=1, data={"vp": 3}, painting=7),   # 3 VP
        
        # === TOOL CARD (1 card) ===
        Card("add_tool", cost=1, painting=6),   # +1 tool
        
        # === WHEAT/FOOD PRODUCTION CARDS (2 cards) ===
        Card("add_wheat", cost=1, multiplier=41),  # +1 food production
        Card("add_wheat", cost=1, painting=8),  # +1 food production
        
        # === DRAW CARD (1 card) ===
        Card("draw_card", cost=3, painting=3),  # draw extra card
        
        # === ONE-USE TOOL CARDS (3 cards) ===
        Card("one_use_tool", cost=1, data={"tool_value": 4}, multiplier=11),  # 4 tool
        Card("one_use_tool", cost=1, data={"tool_value": 3}, multiplier=11),  # 3 tool  
        Card("one_use_tool", cost=1, data={"tool_value": 2}, multiplier=12),  # 2 tool
        
        # === ANY 2 RESOURCES (1 card) ===
        Card("any_2_resources", cost=1, painting=4),  # 2 resources of choice
    ]
    
    if shuffle:
        random.shuffle(cards)
    
    return cards


def create_building_tiles() -> list:
    """
    All 28 building tiles. Resources: 3=wood, 4=stone, 5=clay/brick, 6=gold.
    A fixed-resource building scores the sum of its resources.
    """
    return [
        # 2 of one kind + 1 other
        CertainBuilding(resources=[3, 3, 5]),      # 2 wood + 1 brick = 11 pts
        CertainBuilding(resources=[3, 3, 4]),      # 2 wood + 1 stone = 10 pts
        CertainBuilding(resources=[3, 4, 3]),      # 2 wood + 1 stone = 10 pts
        CertainBuilding(resources=[3, 5, 5]),      # 1 wood + 2 brick = 13 pts
        CertainBuilding(resources=[3, 3, 6]),      # 2 wood + 1 gold = 12 pts
        CertainBuilding(resources=[6, 6, 3]),      # 2 gold + 1 wood = 15 pts
        CertainBuilding(resources=[3, 4, 4]),      # 1 wood + 2 stone = 11 pts
        CertainBuilding(resources=[5, 5, 4]),      # 2 brick + 1 stone = 14 pts
        CertainBuilding(resources=[5, 5, 6]),      # 2 brick + 1 gold = 16 pts
        CertainBuilding(resources=[5, 4, 4]),      # 1 brick + 2 stone = 13 pts
        CertainBuilding(resources=[4, 4, 6]),      # 2 stone + 1 gold = 14 pts
        # 3 different kinds
        CertainBuilding(resources=[3, 5, 4]),      # wood + brick + stone = 12 pts
        CertainBuilding(resources=[3, 5, 6]),      # wood + brick + gold = 14 pts
        CertainBuilding(resources=[3, 4, 6]),      # wood + stone + gold = 13 pts
        CertainBuilding(resources=[3, 4, 6]),      # wood + stone + gold = 13 pts
        CertainBuilding(resources=[5, 4, 6]),      # brick + stone + gold = 15 pts
        CertainBuilding(resources=[4, 5, 6]),      # stone + brick + gold = 15 pts
        CertainBuilding(resources=[6, 5, 4]),      # gold + brick + stone = 15 pts
        # Flexible: N resources of K different kinds, scores the resources paid
        FlexBuilding(resources_require_count=4, variety=1),
        FlexBuilding(resources_require_count=4, variety=2),
        FlexBuilding(resources_require_count=4, variety=3),
        FlexBuilding(resources_require_count=4, variety=4),
        FlexBuilding(resources_require_count=5, variety=1),
        FlexBuilding(resources_require_count=5, variety=2),
        FlexBuilding(resources_require_count=5, variety=2),
        FlexBuilding(resources_require_count=5, variety=3),
        FlexBuilding(resources_require_count=5, variety=4),
        # 1-7 resources of any kind
        FlexBuilding(resources_require_count=7, variety=None),
    ]


def create_building_decks(shuffle: bool = True, stacks: int = 4) -> dict[int, list]:
    """
    Shuffle the 28 building tiles and deal them into 4 stacks of 7, as in the
    board game. The game puts the top tile of each stack on the board.

    Returns:
        Dict mapping stack index (0-3) to its list of Building objects (top first)
    """
    tiles = create_building_tiles()
    if shuffle:
        random.shuffle(tiles)
    size = len(tiles) // stacks
    return {i: tiles[i * size:(i + 1) * size] for i in range(stacks)}
