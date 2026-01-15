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
        self.AI = AI
        
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
        self.multipliers: dict[str, int] = {
            'tools': 0,      # VP per tool value
            'buildings': 0,  # VP per building owned
            'workers': 0,    # VP per worker
            'wheat': 0,      # VP per wheat
        }

    def decide_action(self, possible_actions) -> tuple:
        """
        Decide which action to take (human or AI controlled).
        
        If this is a human player, prompts for input. If AI player,
        delegates to AI decision logic (currently not implemented).
        
        Args:
            possible_actions: List of available actions the player can take.
        
        Returns:
            tuple: (action_choice, amount) representing the chosen action.
        """
        if self.AI is False:
            # Human player: prompt for input
            action = int(input(f"{possible_actions}"))
            amount = int(input("Enter amount: "))
            print(f"Player action chosen: {action}, amount: {amount}")
            print(self.resources)
            return action, amount
        else:
            # AI player: decision logic goes here
            pass

    def get_resource_with_die(self, resource_type: int, dice_roll: int) -> None:
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
        tools = self.decide_to_use_tool(dice_roll, resource_type)
        
        # Calculate gained amount: dice value / resource type (easier with higher dice)
        gained = dice_roll // (resource_type + tools)
        self.resources[resource_type] += gained
        print(f"Gained {gained} of resource {resource_type} (dice {dice_roll}, tools {tools})")

    def decide_to_buy_flex_build_card(self, amount, variety, less_or_equal_variety: bool, 
                                      state=None) -> tuple:
        """
        Decide whether to purchase a flexible building and which resources to spend.
        
        For flexible buildings, player must choose which specific resources to spend
        (within variety constraints). If human player, prompts interactively.
        If AI player, delegates to AI logic.
        
        Args:
            amount (int): Total resources to spend.
            variety (int): Maximum different resource types allowed.
            less_or_equal_variety (bool): If True, can use <=variety types.
                                         If False, must use exactly variety types.
            state: Game state (for AI decision-making).
        
        Returns:
            tuple: (spent_resources_list, purchase_confirmed) or (0, False) if declined.
        """
        if self.AI is False:
            # Human player: interactive purchase decision
            ans = input("Decide to buy (y/n): ")
            print(f"Player decision to buy: {ans}")
            
            if ans.lower() == 'y':
                print(f"Available resources to spend: {self.resources}")
                
                confirmed = False
                while not confirmed:
                    spent_resources = []
                    valid = False
                    
                    # Prompt for each resource to spend
                    for i in range(amount):
                        resource_type = int(input(
                            f"Choose resource type {i+1}/{amount} "
                            "(3=wood, 4=stone, 5=clay, 6=gold): "
                        ))
                        spent_resources.append(resource_type)
                    
                    # Validate variety constraint
                    if less_or_equal_variety:
                        if len(set(spent_resources)) <= variety:
                            valid = True
                    else:
                        if len(set(spent_resources)) == variety:
                            valid = True
                    
                    # Get confirmation
                    if valid:
                        print(f"Spent resources: {spent_resources}")
                        confirm = input("Confirm these choices? (y/n): ")
                        if confirm.lower() == 'y':
                            for resource_type in spent_resources:
                                if less_or_equal_variety == False:
                                    return (spent_resources, True)
                            confirmed = True
                        else:
                            print("Let's try again...")
            
            return (0, False)
        else:
            # AI player: decision logic goes here
            pass
    
    def decide_to_buy_build(self) -> str:
        """
        Decide whether to purchase a certain building.
        
        For buildings with fixed requirements, player simply decides yes or no.
        
        Returns:
            str: "y" if player wants to buy, "n" otherwise.
        """
        if self.AI == False:
            ans = input("Decide to buy (y/n): ")
            print(f"Player decision to buy: {ans}")
            return ans
        else:
            # AI player: decision logic goes here
            pass

    def decide_to_use_tool(self, dice_sum: int, resource_type: int) -> int:
        """
        Decide whether to use tools when gathering resources.
        
        Tools improve dice rolls, making resource gathering more efficient.
        Player can use persistent tools (multiple times) and/or single-use
        tools (once each).
        
        Args:
            dice_sum (int): The dice roll result.
            resource_type (int): Type of resource being gathered (2-6).
        
        Returns:
            int: Total tool value being used (added to effective dice value).
        """
        used_tool = 0
        
        # Calculate total available tool value
        total_tools = (sum(v[0] for v in self.tools) + 
                      sum(v for v in self.one_use_tools if v is not None))
        
        if self.AI is False and total_tools > 0:
            # Human player: ask if they want to use tools
            print(f"Decide to use tool for dice sum {dice_sum} and "
                  f"resource type {resource_type} (y/n): ")
            
            if input().lower() == 'y':
                # Ask about each persistent tool
                for i in range(4):
                    tool_value = self.tools[i][0]
                    tool_available = self.tools[i][1]
                    print(f"Do you want to use tool with value {tool_value} (y/n): ")
                    
                    if input().lower() == 'y' and tool_available is True:
                        self.tools[i][1] = False  # Mark as used (reset later)
                        used_tool += tool_value
                
                # Ask about single-use tools
                for idx, tool in enumerate(self.one_use_tools):
                    if tool is not None:
                        input_t = input(
                            f"Do you want to use a one-time tool with value {tool} (y/n): "
                        )
                        if input_t.lower() == 'y':
                            used_tool += tool
                            self.one_use_tools[idx] = None  # Remove after use
        else:
            # AI player: decision logic goes here
            pass
        
        print(f"Total tool value used: {used_tool}")
        return used_tool

    def choose_resources(self, resource_amount: int) -> int:
        """
        Choose which resource type to receive.
        
        Used when a card or effect grants resources and player chooses the type.
        
        Args:
            resource_amount (int): Amount of resources to choose.
        
        Returns:
            int: Resource type chosen (2-6).
        """
        if self.AI is False:
            print(f"Decide which resource to get in amount of {resource_amount}: "
                  "2-food 3-wood 4-stone 5-clay 6-gold: ")
            choice = int(input())
            print(f"Player chose resource: {choice} (amount {resource_amount})")
            return choice
        else:
            # AI player: decision logic goes here
            pass

    def choose_reward_and_apply(self, dice_rolls: list[int]) -> int:
        """
        Choose a reward from dice roll options and apply it.
        
        Used for dice-based card effects where player chooses among options.
        
        Args:
            dice_rolls (list[int]): Available dice roll options.
        
        Returns:
            int: Reward choice (1-6 representing different reward types).
        """
        if self.AI is False:
            print(f"Available are {dice_rolls}. Decide which resource to get: "
                  "1-wood 2-clay 3-stone 4-gold 5-tool 6-wheat: ")
            choice = int(input())
            print(f"Player chose reward: {choice} from {dice_rolls}")
            return choice
        else:
            # AI player: decision logic goes here
            pass

    def get_reward(self, reward: int) -> None:
        """
        Apply a reward to the player (resources, tools, or wheat).
        
        Args:
            reward (int): Reward type (1-6).
                         1-4: Resource types
                         5: Tool
                         6: Wheat
        """
        print(f"Applying reward {reward}")
        if 1 <= reward <= 4:
            self.get_resources(reward)
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
        print(f"Player gained {amount} of resource {type}; total now {self.resources[type]}")

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
        self.tools[min_tool][0] += 1
        print(f"Upgraded tool slot {min_tool} to value {self.tools[min_tool][0]}")

    def get_one_use_tool(self, tool_value: int) -> None:
        """
        Acquire a single-use tool.
        
        Single-use tools can be used once then are discarded.
        
        Args:
            tool_value (int): Value of the tool (added to dice when used).
        """
        self.one_use_tools.append(tool_value)
        print(f"Added one-use tool with value {tool_value}")

    def get_wheat(self, amount: int = 1) -> None:
        """
        Add wheat to player's supply.
        
        Wheat is used at round end to reduce food cost for feeding workers.
        
        Args:
            amount (int): Wheat to add (default: 1).
        """
        self.wheat += amount
        print(f"Gained {amount} wheat; total wheat {self.wheat}")
    
    def get_worker(self, amount: int = 1) -> None:
        """
        Increase player's worker count.
        
        More workers means more placement options per round.
        
        Args:
            amount (int): Workers to add (default: 1).
        """
        self.total_workers += amount
        print(f"Gained {amount} worker(s); total workers {self.total_workers}")

    def get_card(self, card_end_game_effect) -> None:
        """
        Acquire a card and add it to a collection.
        
        Cards provide end-game scoring. Cards are organized into two decks.
        
        Args:
            card_end_game_effect: Card data to store in collection.
        """
        print(f"Player acquired card: {card_end_game_effect}")
        if card_end_game_effect in self.card_effects[0]:
            # If card exists in deck 0, move to deck 1
            self.card_effects[1].append(card_end_game_effect)
        else:
            # Otherwise add to deck 0
            self.card_effects[0].append(card_end_game_effect)

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
            + self.multipliers['tools'] * sum(v[0] for v in self.tools)
            + self.multipliers['buildings'] * self.building_num
            + self.multipliers['workers'] * self.total_workers
            + self.multipliers['wheat'] * self.wheat
        )
        return vp

    def feed(self) -> None:
        """
        Feed all workers at round end.
        
        Each worker requires 1 food to feed. Wheat can substitute for food.
        Penalty of -10 VP if insufficient food after wheat usage.
        
        Formula: food_used = total_workers - wheat
        """
        # Check for food shortage
        food_available = self.resources[2]  # Food resource
        food_needed = self.total_workers - self.wheat
        
        if food_available < food_needed:
            # Not enough food even with wheat
            self.vp -= 10
            print(f"Not enough food: applying penalty, VP now {self.get_vp()}")
        
        # Consume food
        self.resources[2] = max(0, self.resources[2] - self.total_workers + self.wheat)
        print(f"After feeding: food={self.resources[2]}, wheat carried={self.wheat}, "
              f"total_workers={self.total_workers}")