
from matplotlib.pylab import Any


class Area:
    def __init__(self,capacity: int, resource_type: str) -> None:
        self.resource_type = resource_type
        self.capacity = capacity
        self.occupants: dict[int, int] = {}  # Dictionary of (player, count)
    
    def place(self, player: Any, count: int) -> bool:
        """Place `count` workers for `player` in this area.

        """
        current_occupancy = sum(c for _, c in self.occupants)
        if current_occupancy + count <= self.capacity:
            self.occupants[player] = self.occupants.get(player, 0) + count
        
    def is_occupied(self) -> bool:
        """Check if the location is occupied."""
        return self.occupants is not None
