
class Utility:
    def __init__(self, name: str, capacity: int) -> None:
        self.name = name
        self.capacity = capacity
        self.occupants = None  # Dictionary of (player, count)
    
    def place(self, player: int):
        """Place `count` workers for `player` in this area.

        """
        self.occupants = player