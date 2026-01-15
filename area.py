"""
Area module for Stone Age board game locations.

This module defines the abstract Area class and concrete implementations
(Gathering areas, utilities, buildings, cards) that represent board locations
where players can place workers to gather resources or purchase items.

Classes:
    Area: Abstract base class for all board locations.
    Gathering: Concrete area for resource gathering (wood, stone, clay, gold).
"""

from typing import Any
from abc import ABC, abstractmethod


class Area(ABC):
    """
    Abstract base class for all areas/locations on the Stone Age board.
    
    An Area is a board location where players can place workers to perform
    actions. Each area has a capacity limit and tracks which players have
    placed workers there.
    
    Attributes:
        capacity (int): Maximum number of workers that can be placed in this area.
        occupants (dict[int, int]): Maps player index (0-3) to worker count placed
                                   by that player in this area.
    """
    
    def __init__(self, capacity: int):
        """
        Initialize an Area with a given capacity.
        
        Args:
            capacity (int): Maximum number of workers allowed in this area.
        
        Initializes occupants dictionary with 0 workers for each of 4 players.
        """
        self.capacity = capacity
        # Track workers placed by each player (players indexed 0-3)
        self.occupants: dict[int, int] = {
            0: 0,  # Player 0 workers
            1: 0,  # Player 1 workers
            2: 0,  # Player 2 workers
            3: 0   # Player 3 workers
        }

    def place(self, player_index: int, count: int = 1) -> bool:
        """
        Place workers for a player in this area.
        
        Increases the count of workers belonging to the specified player
        in this area. Note: This method assumes capacity checks are done
        by the caller via can_place().
        
        Args:
            player_index (int): Index of the player (0-3).
            count (int): Number of workers to place (default: 1).
        
        Returns:
            bool: Currently not used (returns None). Should return True if
                 placement succeeded, False otherwise.
        """
        self.occupants[player_index] = self.occupants.get(player_index, 0) + count

    @abstractmethod
    def name(self) -> str:
        """
        Return a descriptive name for this area.
        
        Subclasses must implement this method to provide a meaningful name
        for the location (e.g., "Food Gathering", "Hut", "Tool Shop").
        
        Returns:
            str: Descriptive name of the area.
        """
        pass

    def clear(self) -> None:
        """
        Remove all workers from this area.
        
        Called at the start of each round to reset occupancy.
        After clearing, all players will have 0 workers here.
        """
        self.occupants.clear()
        # Reinitialize with zeros for all players
        for i in range(4):
            self.occupants[i] = 0
    
    def is_occupied(self, player_index: int) -> bool:
        """
        Check if a specific player has workers in this area.
        
        Args:
            player_index (int): Index of the player to check (0-3).
        
        Returns:
            bool: True if player has at least 1 worker here, False otherwise.
        """
        return self.occupants.get(player_index, 0) > 0
    
    def can_place(self, try_to_place: int = 1) -> bool:
        """
        Check if workers can be placed in this area without exceeding capacity.
        
        Calculates the total current occupancy and checks if adding try_to_place
        workers would exceed the area's capacity.
        
        Args:
            try_to_place (int): Number of workers trying to be placed (default: 1).
        
        Returns:
            bool: True if placement is possible, False if it would exceed capacity.
        """
        # Sum all workers currently in the area (from all players)
        current_occupancy = sum(v for v in self.occupants.values())
        
        # Check if adding more would exceed capacity
        if current_occupancy + try_to_place <= self.capacity:
            return True
        return False
    
    def available_space(self) -> int:
        """
        Calculate the number of empty slots in this area.
        
        Returns how many more workers could be placed here before hitting capacity.
        
        Returns:
            int: Number of available worker slots (capacity - current_occupancy).
        """
        current_occupancy = sum(v for v in self.occupants.values())
        return self.capacity - current_occupancy
    
    def is_able_to_buy(self) -> bool:
        """
        Check if a player can afford to buy/use this area (abstract).
        
        This method is defined differently for different area types:
        - Gathering areas: Not applicable, no cost
        - Buildings: Player must have enough resources
        - Cards: Player must have enough resources
        
        Subclasses should override this method if applicable.
        
        Returns:
            bool: True if purchase/use is possible, False otherwise.
        """
        pass


class Gathering(Area):
    """
    A Gathering area where players place workers to collect resources.
    
    When workers are placed here, they collect a specific resource type
    (food, wood, stone, clay, or gold). The type of resource and quantity
    gathered depends on the number of workers and any tools the player uses.
    
    Attributes:
        resource_type (str): Type of resource gathered here (e.g., "wood", "stone").
        capacity (int): Maximum workers allowed (inherited from Area).
        occupants (dict[int, int]): Worker placement by player (inherited from Area).
    """
    
    def __init__(self, capacity: int, resource_type: str) -> None:
        """
        Initialize a Gathering area for collecting a specific resource.
        
        Args:
            capacity (int): Maximum number of workers that can gather here.
            resource_type (str): Type of resource collected (2=food, 3=wood,
                                4=stone, 5=clay, 6=gold). Often stored as integer
                                but this parameter suggests string usage.
        """
        self.resource_type = resource_type
        super().__init__(capacity)

    def name(self) -> str:
        """
        Return a descriptive name for this gathering area.
        
        Returns:
            str: Description indicating this is a resource gathering area
            and which resource can be collected.
        """
        return f"can collect {self.resource_type}"