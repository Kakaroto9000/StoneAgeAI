from area import Area
class Utility(Area):
    def __init__(self, name: str, capacity: int) -> None:
        self.name = name
        super().__init__(capacity)

    def name(self) -> str:
        return self.name()