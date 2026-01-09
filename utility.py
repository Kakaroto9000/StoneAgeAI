
class Utility:
    def __init__(self, name: str, capacity: int) -> None:
        self.name = name
        self.capacity = capacity
        self.occupants: int | None = None  # Dictionary of (player, count)
    
    def place(self, player: int) -> None:
        """Place `count` workers for `player` in this area.

        """
        self.occupants = player
    def is_occupied(self) -> bool:
        """Check if the location is occupied."""
        return self.occupants is not None
    
    def clear(self) -> None:
        """Clear the occupant from the utility."""
        self.occupants = None