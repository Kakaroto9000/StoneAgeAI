from matplotlib.pylab import Any

class Area():
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.occupants: dict[int,int] = {}

    def place(self, player: Any, count: int = 1) -> bool:
        """Place `count` workers for `player` in this area.

        """
        current_occupancy = sum(c for _, c in self.occupants)
        if current_occupancy + count <= self.capacity:
            self.occupants[player] = self.occupants.get(player, 0) + count
    
    def clear(self) -> None:
        """Clear all occupants from the area."""
        self.occupants.clear()
    
    def is_occupied(self) -> bool:
        """Check if the location is occupied."""
        return self.occupants is not None
    
    def can_place(self, try_to_place: int = 1):
        current_occupancy = sum(c for _, c in self.occupants)
        if current_occupancy+ try_to_place <= self.capacity:
            return True
        return False

class Gathering(Area):
    def __init__(self,capacity: int, resource_type: str) -> None:
        self.resource_type = resource_type
        super.__init__(capacity)
    
    

