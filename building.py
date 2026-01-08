from matplotlib.pylab import Any


class Building:
    def __init__(self, resources: list) -> None:
        self.resources = resources
        self.capacity = 1
        self.occupants = None  # Dictionary of (player, count)
    
    def place(self, player: int):
        """Place `count` workers for `player` in this area.

        """
        self.occupants = player
