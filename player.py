"""
Player module for Stone Age board game players.

This module defines the Player class, which represents a player in the Stone Age
game. Players manage resources, workers, tools, buildings, and cards. They also
make decisions (either via AI or human input) about purchasing and tool usage.

Classes:
    Player: Represents a single player with resources, workers, and inventory.
"""


class Player:
    """
    Represents a player in the Stone Age board game.
    
    Manages all aspects of a player's game state:
    - Workers: Total and available for placement
    - Resources: Food, wood, stone, clay, gold
    - Tools: Persistent and single-use
    - Buildings: Number owned
    - Cards: Collected cards with special effects
    - Victory points: From various sources
    - Wheat: Special resource for feeding
    
    Attributes:
        wheat (int): Wheat collected (helps feed workers, reduces food cost).
        total_workers (int): Total number of workers player can place each round.
        available_workers (int): Workers not yet placed this round.
        vp (int): Direct victory points.
        vp_buildings (int): Victory points from purchased buildings.
        AI (bool): Whether this is an AI player or human player.
        resources (dict[int, int]): Resource inventory by type.
                                   Keys: 2=food, 3=wood, 4=stone, 5=clay, 6=gold.
        tools (list[list]): Persistent tools. Each tool is [value, available].
        building_num (int): Number of buildings owned.
        one_use_tools (list[int]): Single-use tools with their values.
        card_effects (dict[int, list[int]]): Cards by collection.
                                            0=painting deck, 1=other deck.
        multipliers (dict[str, int]): End-game scoring multipliers.
    """
    
    def __init__(self, food: int = 10, workers: int = 5, AI: bool = False) -> None:
        """
        Initialize a Player with starting resources and workers.
        
        Args:
            food (int): Starting food resources (default: 10).
            workers (int): Starting number of workers (default: 5).
            AI (bool): Whether this player is controlled by AI (default: False).
        """
        self.wheat = 0
        self.total_workers = workers
        self.available_workers = workers
        self.vp = 0  # Victory points
        self.vp_buildings = 0  # Victory points from buildings
        
        # Resource inventory: food, wood, stone, clay, gold
        self.resources = {
            2: food,  # Food (starting resource)
            3: 0,     # Wood
            4: 0,     # Stone
            5: 0,     # Clay
            6: 0,     # Gold
        }
        
        # Persistent tools: [value, is_available]
        # Each element is [current_tool_value, whether_tool_can_be_used]
        self.tools = [
            [0, True],   # Tool slot 1
            [0, True],   # Tool slot 2
            [0, True],   # Tool slot 3
            [0, True]    # Tool slot 4
        ]
        
        self.building_num = 0  # Number of buildings owned
        
        # Single-use tools that can be used once then discarded
        self.one_use_tools: list[int] = []
        
        # Card collections organized by type/deck
        self.card_effects: dict[int, list[int]] = {
            0: [],  # Painting deck (art/culture cards)
            1: [],  # Other deck (science/etc)
        }
        
        # End-game scoring multipliers
        self.multipliers: dict[int, int] = {
            1: 0,      # VP per tool value
            2: 0,  # VP per building owned
            3: 0,    # VP per worker
            4: 0,      # VP per wheat
        }


    def get_resource_with_die(self, resource_type: int, dice_roll: int, tools: list[int]) -> None:
        """
        Gain resources based on a dice roll.
        
        The amount gained is dice_roll divided by resource_type (in Stone Age,
        higher numbers = harder to gather). Tools modify the dice result before
        division.
        
        Args:
            resource_type (int): Type of resource to gather (2-6).
            dice_roll (int): Sum of dice roll (determines base amount).
        """
        # Decide if using tools to improve this gathering
        tools_used = self.use_tool(tools)
        # Calculate gained amount: dice value / resource type (easier with higher dice)
        gained = (dice_roll + tools_used) // resource_type
        self.resources[resource_type] += gained
        
    def use_tool(self, tools):
        used_tools_sum = 0
        for index, _ in enumerate(self.tools):
            if tools[index] == 1:
                self.tools[index][1] = False
                used_tools_sum += self.tools[index][0]
        to_remove = []
        for index, _ in enumerate(self.one_use_tools):
            if tools[index + 4] == 1:
                used_tools_sum += self.one_use_tools[index]
                to_remove.append(index)
        for i in reversed(to_remove):
            self.one_use_tools.pop(i)
        return used_tools_sum
                

    def get_reward(self, reward: int) -> None:
        """
        Apply a reward to the player (resources, tools, or wheat).
        
        Args:
            reward (int): Reward type (1-6).
                         1-4: Resource types
                         5: Tool
                         6: Wheat
        """
        if 1 <= reward <= 4:
            self.get_resources(reward+2)
        elif reward == 5:
            self.get_tool()
        else:
            self.get_wheat()

    def get_resources(self, type: int, amount: int = 1) -> None:
        """
        Add resources to player's inventory.
        
        Args:
            type (int): Resource type (2-6).
            amount (int): Quantity to add (default: 1).
        """
        self.resources[type] += amount

    def lose_resources(self, resources: list[int]) -> None:
        """
        Remove specified resources from player's inventory.
        
        Used when purchasing buildings or cards. Each element in the list
        represents one unit of that resource type to spend.
        
        Args:
            resources (list[int]): List of resource types to lose (one per element).
        """
        for resource in resources:
            self.resources[resource] -= 1

    def get_tool(self) -> None:
        """
        Upgrade one of the player's tool slots.
        
        Finds the weakest tool and increases its value by 1.
        Tools help with resource gathering.
        """
        # Find tool slot with minimum value
        min_tool = 0
        for i in range(1, 4):
            if self.tools[i][0] < self.tools[min_tool][0]:
                min_tool = i
        
        # Upgrade that slot
        if sum(v[0] for v in self.tools)<16:
            self.tools[min_tool][0] += 1

    def get_one_use_tool(self, tool_value: int) -> None:
        """
        Acquire a single-use tool.
        
        Single-use tools can be used once then are discarded.
        
        Args:
            tool_value (int): Value of the tool (added to dice when used).
        """
        self.one_use_tools.append(tool_value)

    def refresh_tools(self):
        for tool in self.tools:
            tool[1] = True

    def get_wheat(self, amount: int = 1) -> None:
        """
        Add wheat to player's supply.
        
        Wheat is used at round end to reduce food cost for feeding workers.
        
        Args:
            amount (int): Wheat to add (default: 1).
        """
        if self.wheat<10:
            self.wheat += amount
    
    def get_worker(self, amount: int = 1) -> None:
        """
        Increase player's worker count.
        
        More workers means more placement options per round.
        
        Args:
            amount (int): Workers to add (default: 1).
        """
        if self.total_workers < 10:
            self.total_workers += amount

    def get_card(self, card_end_game_effect) -> None:
        """
        Acquire a card and add it to a collection.
        
        Cards provide end-game scoring. Cards are organized into two decks.
        
        Args:
            card_end_game_effect: Card data to store in collection.
        """
        if card_end_game_effect<10:
            if card_end_game_effect in self.card_effects[0]:
            # If card exists in deck 0, move to deck 1
                self.card_effects[1].append(card_end_game_effect)
            else:
            # Otherwise add to deck 0
                self.card_effects[0].append(card_end_game_effect)
        else:
            self.multipliers[card_end_game_effect//10] += card_end_game_effect%10
        

    def get_vp(self) -> int:
        """
        Calculate total victory points including multipliers.
        
        Victory points come from:
        - Direct VP (self.vp)
        - Buildings (self.vp_buildings)
        - Tools × tool multiplier
        - Buildings owned × building multiplier
        - Workers × worker multiplier
        - Wheat × wheat multiplier
        
        Returns:
            int: Total victory points.
        """
        vp = (
            self.vp
            + self.vp_buildings
            + self.multipliers[1] * sum(v[0] for v in self.tools)
            + self.multipliers[2] * self.building_num
            + self.multipliers[3] * self.total_workers
            + self.multipliers[4] * self.wheat
            + self.drawings_vp()
        )
        return vp
    
    def drawings_vp(self):
        vp = 0
        for i in range(2):
            vp+= len(self.card_effects[i])*len(self.card_effects[i])
        return vp
    
    def get_score(self) -> list[int]:
        return [self.resources, self.wheat, self.total_workers, self.get_vp(), self.tools, sum(v for v in self.one_use_tools), self.multipliers.values()]

    def feed(self) -> None:
        food_available = self.resources[2]
        food_needed = max(0, self.total_workers - self.wheat)  # Can't be negative
    
        if food_available < food_needed:
            self.vp -= 10
    
        # Consume only what's needed
        self.resources[2] = max(0, self.resources[2] - food_needed)