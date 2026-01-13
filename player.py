
class Player:
    def __init__(self, food: int = 10, workers: int = 5, AI: bool = False) -> None:
        self.wheat = 0
        self.total_workers = workers
        self.available_workers = workers
        self.vp = 0  # Victory points
        self.AI = AI
        self.resources = {
            2: food,  # Food
            3: 0,  # Wood
            4: 0,  # Stone
            5: 0,  # Clay
            6: 0,  # Gold
        }
        self.tools = [
            [0, True],
            [0, True],
            [0, True],
            [0, True]
        ]
        self.one_use_tools: list[int] = []
        self.card_effects: list[int] = []
        self.multipliers: dict[int, int] = {}

    def decide_action(self, possible_actions):
        if self.AI is False:
            action = int(input(f"{possible_actions}"))
            amount = int(input())
            print(f"Player action chosen: {action}, amount: {amount}")
            print(self.resources)
            return action, amount
        else:
            pass

    def get_resource_with_die(self, resource_type: int, dice_roll: int) -> None:
        """Add `amount` of `resource_type` to the player's resources."""
        tools = self.decide_to_use_tool(dice_roll, resource_type)
        gained = dice_roll // (resource_type + tools)
        self.resources[resource_type] += gained
        print(f"Gained {gained} of resource {resource_type} (dice {dice_roll}, tools {tools})")

    def decide_to_buy_flex_build_card(self, amount, variety, less_or_equal_variety: bool, state= None) -> bool:
        """Acquire a new card for the player."""
        if self.AI is False:
            ans = input("Decide to buy (y/n): ")
            print(f"Player decision to buy: {ans}")
            if ans.lower() == 'y':
                print(f"Available resources to spend: {self.resources}")
                
                confirmed = False
                while not confirmed:
                    spent_resources = []
                    valid = False
                    
                    for i in range(amount):
                        resource_type = int(input(f"Choose resource type {i+1}/{variety} ( 3-wood, 4-stone, 5-clay, 6-gold): "))
                        
                        spent_resources.append(resource_type)
                    if less_or_equal_variety:
                        if len(set(spent_resources)) <= variety:
                            valid = True
                    else:
                        if len(set(spent_resources)) == variety:
                            valid = True
                    
                    if valid:
                        print(f"Spent resources: {spent_resources}")
                        confirm = input("Confirm these choices? (y/n): ")
                        if confirm.lower() == 'y':
                            for resource_type in spent_resources:
                                self.lose_resources(resource_type, 1)
                            confirmed = True
                        else:
                            print("Let's try again...")
                
                return True
            return False
        else:
            pass

    def decide_to_use_tool(self, dice_sum: int, resource_type: int) -> int:
        """Decide whether to use a tool when gathering resources."""
        used_tool = 0
        total_tools = sum(v[0] for v in self.tools) + sum(v for v in self.one_use_tools if v is not None)
        if self.AI is False and total_tools > 0:
            print(f"Decide to use tool for dice sum {dice_sum} and resource type {resource_type} (y/n): ")
            if input().lower() == 'y':
                for i in range(4):
                    tool_value = self.tools[i][0]
                    tool_usage = self.tools[i][1]
                    print(f"Do you want to use tool with value {tool_value} (y/n): ")
                    if input().lower() == 'y' and tool_usage is True:
                        self.tools[i][1] = False  # Mark tool as used
                        used_tool += tool_value
                for tool in self.one_use_tools:
                    input_t = input(f"Do you want to use a one time tool with value {tool} (y/n): ")
                    if input_t.lower() == 'y':
                        used_tool += tool
                        tool = None
        else:
            pass
        print(f"Total tool value used: {used_tool}")
        return used_tool

    def choose_resources(self, resource_amount: int):
        if self.AI is False:
            print(f"Decide which resource to get in amount of {resource_amount} 2-food 3-wood 4-clay 5-stone 6-gold: ")
            choice = int(input())
            print(f"Player chose resource: {choice} (amount {resource_amount})")
            return choice
        else:
            pass

    def choose_reward_and_apply(self, dice_rolls: list[int]):
        if self.AI is False:
            print(f"avaliable are {dice_rolls} Decide which resource to get 1-wood 2-clay 3-stone 4-gold 5-tool 6-wheat: ")
            choice = int(input())
            print(f"Player chose reward: {choice} from {dice_rolls}")
            return choice
        else:
            pass

    def get_reward(self, reward: int):
        print(f"Applying reward {reward}")
        if 1<=reward<=4:
            self.get_resources(reward)
        elif reward == 5:
            self.get_tool()
        else:
            self.get_wheat()

    def get_resources(self, type: int, amount: int = 1):
        self.resources[type] += amount
        print(f"Player gained {amount} of resource {type}; total now {self.resources[type]}")

    def lose_resources(self, resource: int, amount: int):
        self.resources[resource] -= amount

    def get_tool(self) -> None:
        """Acquire a new tool for the player."""
        min_tool = self.tools[0][0]
        for i in range(1,4):
            if self.tools[i][0] < self.tools[min_tool][0]:
                min_tool = i
        self.tools[min_tool][0] += 1
        print(f"Upgraded tool slot {min_tool} to value {self.tools[min_tool][0]}")
        self.check_vp()

    def get_one_use_tool(self, tool_value: int) -> None:
        """Add a one-use tool with `tool_value` to the player's tools."""
        self.one_use_tools.append(tool_value)
        print(f"Added one-use tool with value {tool_value}")
        self.check_vp()

    def get_wheat(self, amount: int) -> None:
        """Add `amount` of wheat to the player's resources."""
        self.wheat += amount
        print(f"Gained {amount} wheat; total wheat {self.wheat}")
        self.check_vp()
    
    def get_worker(self, amount: int) -> None:
        """Add `amount` of workers to the player's total and available workers."""
        self.total_workers += amount
        print(f"Gained {amount} worker(s); total workers {self.total_workers}")
        self.check_vp()

    def get_card(self, card_end_game_effect) -> None:
        """Acquire a new card for the player."""
        print(f"Player acquired card: {card_end_game_effect}")
        self.card_effects.append(card_end_game_effect)

    def check_vp(self) -> None:
        """Check and update victory points based on tools owned."""
        print(f"Check VP called. Current VP: {self.vp}")

    def feed(self) -> int:
        """Feed the player and return score change based on food shortage."""
        if self.resources[2] - self.wheat < self.total_workers:
            self.vp -=10  # penalty for not feeding
            print(f"Not enough food: applying penalty, VP now {self.vp}")
        self.resources[2] = max(0, self.resources[2] - self.total_workers + self.wheat)
        print(f"After feeding: food={self.resources[2]}, wheat carried={self.wheat}, total_workers={self.total_workers}")
