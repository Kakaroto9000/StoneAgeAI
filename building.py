from typing import Dict, Optional
from abc import ABC, abstractmethod
from area import Area

class Building(Area):
    def __init__(self) -> None:
        super.__init__(1)
    
    @abstractmethod
    def is_able_to_buy(self, player_resources: Dict[int, int]) -> bool:
        """Check if a player has enough resources to buy this building.

        """

class CertainBuilding(Building):
    def __init__(self, resources: Dict[int, int]) -> None:
        super().__init__()
        self.resources = resources

    def is_able_to_buy(self, player_resources: Dict[int, int]) -> bool:
        """Check if a player has enough resources to buy this building.

        """
        for resource, value in self.resources.items():
            if player_resources.get(resource, 0) < value:
                return False
        return True

class FlexBuilding(Building):
    def __init__(self, resources_require_count: int, variety: Optional[int] = None) -> None:
        super().__init__()
        self.resources_require_count = resources_require_count
        self.variety = variety

    def is_able_to_buy(self, player_resources: Dict[int, int]) -> bool:
        """Check if a player has enough resources to buy this building.

        """
        if self.resources_require_count == 7:
            return any(v > 0 for v in player_resources.values())
        # Get the resource counts, sorted in descending order
        counts = sorted(player_resources.values(), reverse=True)
        # Sum the top 'variety' counts (or all if variety is None or more than available)
        total = sum(counts[:self.variety])
        return (total >= self.resources_require_count and all(v>0 for v in counts[:self.variety]))
