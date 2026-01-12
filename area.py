from typing import Any
from abc import ABC, abstractmethod

class Area(ABC):
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.occupants: dict[int,int] = {
        }

    def place(self, player_index: int, count: int = 1) -> bool:
        """Place `count` workers for `player` in this area.

        """
        self.occupants[player_index] = self.occupants.get(player_index, 0) + count

    @abstractmethod
    def name(self) -> str:
        pass

    def clear(self) -> None:
        """Clear all occupants from the area."""
        self.occupants.clear()
    
    def is_occupied(self, player_index) -> bool:
        """Check if the location is occupied."""
        return self.occupants.get(player_index, 0)> 0
    
    def can_place(self, try_to_place: int = 1):
        current_occupancy = sum(v for v in self.occupants.values())
        if current_occupancy+ try_to_place <= self.capacity:
            return True
        return False
    
    def avaliable_space(self) -> int:
        return self.capacity - sum(v for v in self.occupants.values())

class Gathering(Area):
    def __init__(self,capacity: int, resource_type: str) -> None:
        self.resource_type = resource_type
        super().__init__(capacity)

    def name(self) -> str:
        return (f"can collect {self.resource_type}")
