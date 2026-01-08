class Card:
    def __init__(self, cost: int) -> None:
        self.cost = cost
        self.capacity = 1
        self.occupants = None  # Dictionary of (player, count)
    
    def place(self, player: int):
        """Place `count` workers for `player` in this area.

        """
        self.occupants = player
