"""
Utility module for Stone Age board game utilities.

This module defines the Utility class, which represents special board locations
like the Farm (for wheat), House (for workers), and Tool Shop. Unlike buildings
and cards, utilities are always available and can be used multiple times.

Classes:
    Utility: Special board locations with generic functionality.
"""

from area import Area


class Utility(Area):
    """
    A Utility area - a special board location with a specific function.
    
    Utilities are permanent board locations (unlike cards which get purchased
    and replaced). Examples include the Farm (gain wheat), House (gain workers),
    and Tool Shop (gain tools). Multiple players can use the same utility.
    
    Utilities have their capacity set at initialization and maintain a custom name.
    
    Attributes:
        n (str): Custom name of this utility (e.g., "Farm", "House", "ToolShop").
        capacity (int): Maximum workers that can be placed here (inherited).
        occupants (dict[int, int]): Worker placement by player (inherited).
    """
    
    def __init__(self, name: str, capacity: int) -> None:
        """
        Initialize a Utility with a name and capacity.
        
        Args:
            name (str): Descriptive name of the utility
            (e.g., "Farm", "House", "ToolShop").
            capacity (int): Maximum number of workers allowed here.
                For example:
            - Farm: typically 1 (limited spots)
            - House: typically 2 (more spots)
            - ToolShop: typically 1 (limited spots)
        """
        self.n = name
        super().__init__(capacity)

    def name(self) -> str:
        """
        Return the name of this utility.
        
        Returns:
            str: The utility's name (set in __init__).
        """
        return self.n