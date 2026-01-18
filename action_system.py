"""
Action System for Stone Age RL.

This module defines the complete action space and provides fast mask generation
using dictionary lookups. Add this to your game.py or import it.

Action Types:
    1: Placement - place workers at a location
    2: Tools - choose which tools to use for gathering
    3: Buy/Skip - decide whether to purchase building/card
    4: Resources - choose which resources to spend
    5: Dice - select a die value from rolled dice
    6: Choose2 - pick 2 resources (from card effect)
"""

import numpy as np
from itertools import product, combinations_with_replacement
from typing import Dict, List, Tuple
from utility import Utility


class ActionSystem:
    """
    Manages the complete action space for Stone Age RL.
    
    Provides:
    - ALL_ACTIONS: List of all possible actions
    - action_to_index: Fast lookup from action tuple to index
    - get_mask(): Generate binary mask for current valid actions
    
    Attributes:
        ALL_ACTIONS (List): Every possible action as a 7-element list
        NUM_ACTIONS (int): Total number of actions
        action_to_index (Dict): Maps action tuples to indices for O(1) lookup
    """
    
    def __init__(self, locations: List):
        """
        Initialize the action system.
        
        Args:
            locations: List of game locations (needed for placement capacities)
        """
        self.locations = locations
        self.ALL_ACTIONS = []
        self.action_to_index = {}
        
        self._build_all_actions()
    
    def _build_all_actions(self):
        """Build complete action list with dictionary lookups."""
        actions = []
        action_to_index = {}
        
        # ============================================================
        # PLACEMENT ACTIONS: (1, location_idx, worker_count)
        # Output format: [location, workers, 0, 0, 0, 0, 0]
        # ============================================================
        self.PLACEMENT_START = len(actions)
        
        for loc_idx, location in enumerate(self.locations):
            if not(isinstance(location, Utility) and location.name() == "House"):
                max_workers = min(location.capacity, 10)  # Cap at 10 workers
                for workers in range(1, max_workers + 1):
                    key = (1, loc_idx, workers)
                    action_to_index[key] = len(actions)
                    actions.append([loc_idx, workers, 0, 0, 0, 0, 0])
            else:
                key = (1, loc_idx, 2)
                action_to_index[key] = len(actions)
                actions.append([loc_idx, 2, 0, 0, 0, 0, 0])
        
        # ============================================================
        # TOOL ACTIONS: (2, t0, t1, t2, t3, o0, o1, o2)
        # Output format: [t0, t1, t2, t3, o0, o1, o2] (binary flags)
        # ============================================================
        self.TOOLS_START = len(actions)
        
        for combo in product([0, 1], repeat=7):
            key = (2,) + combo
            action_to_index[key] = len(actions)
            actions.append(list(combo))
        
        # ============================================================
        # BUY/SKIP ACTIONS: (3, choice)
        # Output format: [choice, 0, 0, 0, 0, 0, 0]
        # ============================================================
        self.BUY_SKIP_START = len(actions)
        
        # Skip = 0
        action_to_index[(3, 0)] = len(actions)
        actions.append([0, 0, 0, 0, 0, 0, 0])
        
        # Buy = 1
        action_to_index[(3, 1)] = len(actions)
        actions.append([1, 0, 0, 0, 0, 0, 0])
        
        # ============================================================
        # RESOURCE SPENDING: (4, wood, stone, clay, gold)
        # Output format: [wood, stone, clay, gold, 0, 0, 0]
        # ============================================================
        self.RESOURCES_START = len(actions)
        
        for cost in range(1, 8):  # 1 to 7 resources
            for combo in combinations_with_replacement([3, 4, 5, 6], cost):
                counts = [combo.count(r) for r in [3, 4, 5, 6]]
                key = (4, counts[0], counts[1], counts[2], counts[3])
                
                # Avoid duplicates (same resource counts can come from different combos)
                if key not in action_to_index:
                    action_to_index[key] = len(actions)
                    actions.append(counts + [0, 0, 0])
        
        # ============================================================
        # DICE SELECTION: (5, die_value)
        # Output format: [die_value, 0, 0, 0, 0, 0, 0]
        # ============================================================
        self.DICE_START = len(actions)
        
        for die_value in range(1, 7):  # 1 to 6
            key = (5, die_value)
            action_to_index[key] = len(actions)
            actions.append([die_value, 0, 0, 0, 0, 0, 0])
        
        # ============================================================
        # CHOOSE 2 RESOURCES: (6, resource1, resource2)
        # Output format: [resource1, resource2, 0, 0, 0, 0, 0]
        # ============================================================
        self.CHOOSE2_START = len(actions)
        
        for combo in product(range(2, 7), repeat=2):  # 2-6 for each
            key = (6, combo[0], combo[1])
            action_to_index[key] = len(actions)
            actions.append([combo[0], combo[1], 0, 0, 0, 0, 0])
        
        # ============================================================
        # Store results
        # ============================================================
        self.ALL_ACTIONS = actions
        self.action_to_index = action_to_index
        self.NUM_ACTIONS = len(actions)
        
        # Print summary
        """
        print(f"Action space built:")
        print(f"  Placement: {self.PLACEMENT_START} - {self.TOOLS_START - 1}")
        print(f"  Tools:     {self.TOOLS_START} - {self.BUY_SKIP_START - 1}")
        print(f"  Buy/Skip:  {self.BUY_SKIP_START} - {self.RESOURCES_START - 1}")
        print(f"  Resources: {self.RESOURCES_START} - {self.DICE_START - 1}")
        print(f"  Dice:      {self.DICE_START} - {self.CHOOSE2_START - 1}")
        print(f"  Choose2:   {self.CHOOSE2_START} - {self.NUM_ACTIONS - 1}")
        print(f"  TOTAL:     {self.NUM_ACTIONS} actions")
        """
    
    def get_action(self, index: int) -> List[int]:
        """Get action list by index."""
        return self.ALL_ACTIONS[index]
    
    def get_index(self, action_type: int, *args) -> int:
        """
        Get index for an action.
        
        Args:
            action_type: 1=placement, 2=tools, 3=buy/skip, 4=resources, 5=dice, 6=choose2
            *args: Action-specific arguments
        
        Returns:
            int: Index into ALL_ACTIONS
        
        Examples:
            get_index(1, 3, 2)        # Place 2 workers at location 3
            get_index(2, 1,0,1,0,0,0,0)  # Use tools 0 and 2
            get_index(3, 1)           # Buy
            get_index(4, 2, 0, 1, 0)  # Spend 2 wood + 1 clay
            get_index(5, 4)           # Select die value 4
            get_index(6, 3, 5)        # Choose wood and clay
        """
        key = (action_type,) + tuple(args)
        return self.action_to_index[key]


class MaskGenerator:
    """
    Generates action masks for the current game state.
    
    Uses dictionary lookups for O(1) per valid action instead of
    O(n) searching through the action list.
    """
    
    def __init__(self, action_system: ActionSystem):
        self.action_system = action_system
    
    def get_mask(self, game) -> np.ndarray:
        """
        Generate binary mask for currently valid actions.
        
        Args:
            game: Game instance with current_type_of_action and helper methods
        
        Returns:
            np.ndarray: Binary mask of shape (NUM_ACTIONS,)
        """
        mask = np.zeros(self.action_system.NUM_ACTIONS, dtype=np.int8)
        idx = self.action_system.action_to_index
        
        action_type = game.current_type_of_action
        
        if action_type == 1:  # Placement
            valid = game.get_valid_actions_for_placement()
            for loc_idx, workers in valid:
                key = (1, loc_idx, workers)
                if key in idx:
                    mask[idx[key]] = 1
        
        elif action_type == 2:  # Tools
            valid = game.get_valid_actions_for_tools_choose()
            for tool_combo in valid:
                key = (2,) + tuple(tool_combo)
                if key in idx:
                    mask[idx[key]] = 1
        
        elif action_type == 3:  # Buy/skip
            mask[idx[(3, 0)]] = 1  # Skip always valid
            if game.locations[game.current_action_data[0]].is_able_to_buy(game.current_player.resources):
                mask[idx[(3, 1)]] = 1
        
        elif action_type == 4:  # Resource spending
            valid = game.get_valid_actions_for_spending_resources()
            for resource_combo in valid:
                # resource_combo is [wood, stone, clay, gold]
                if len(resource_combo) == 4:
                    key = (4, resource_combo[0], resource_combo[1], 
                           resource_combo[2], resource_combo[3])
                    if key in idx:
                        mask[idx[key]] = 1
        
        elif action_type == 5:  # Dice selection
            for die_value in game.current_action_data:
                key = (5, die_value)
                if key in idx:
                    mask[idx[key]] = 1
        
        elif action_type == 6:  # Choose 2 resources
            # All combinations valid
            for i in range(self.action_system.CHOOSE2_START, 
                          self.action_system.NUM_ACTIONS):
                mask[i] = 1
        
        return mask
    
    def get_random_valid_action(self, game) -> int:
        """Get a random valid action index."""
        mask = self.get_mask(game)
        valid_indices = np.where(mask == 1)[0]
        if len(valid_indices) == 0:
            raise ValueError("No valid actions available!")
        return np.random.choice(valid_indices)