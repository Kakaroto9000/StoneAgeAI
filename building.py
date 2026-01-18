"""
Building module for Stone Age board game structures.

This module defines the Building class hierarchy, which represents purchasable
structures on the Stone Age board. Buildings provide victory points and require
specific resources to purchase.

Two building types are implemented:
1. CertainBuilding: Requires exact combination of specific resources
2. FlexBuilding: Requires specific amount/variety of resources (flexible choice)

Classes:
    Building: Abstract base class for purchasable buildings.
    CertainBuilding: Building with fixed resource requirements.
    FlexBuilding: Building with flexible resource requirements.
"""

from typing import Dict, Optional
from abc import ABC, abstractmethod
from area import Area


class Building(Area):
    """
    Abstract base class for purchasable buildings.
    
    Buildings are special areas on the board with limited capacity (usually 1,
    for the single player who purchases it). Buildings provide victory points
    and require resources to purchase.
    
    Inherits from Area to track which player owns it.
    
    Attributes:
        capacity (int): Always 1 (only one player can own each building).
        occupants (dict[int, int]): Tracks which player owns this building.
    """
    
    def __init__(self) -> None:
        """
        Initialize a Building with capacity 1.
        
        Since only one player can own a building, capacity is fixed at 1.
        When a player places 1 worker here, they trigger the purchase.
        """
        super().__init__(1)  # Buildings always have capacity of 1
    
    @abstractmethod
    def is_able_to_buy(self, player_resources: Dict[int, int]) -> bool:
        """
        Check if a player has enough resources to purchase this building.
        
        This is an abstract method that must be implemented by subclasses,
        as different building types have different purchase requirements.
        
        Args:
            player_resources (Dict[int, int]): Player's current resources.
                                              Keys are resource types (2-6),
                                              values are quantities.
        
        Returns:
            bool: True if player can afford this building, False otherwise.
        """
        pass


class CertainBuilding(Building):
    """
    A Building with specific, fixed resource requirements.
    
    The player must provide exactly the specified resources to purchase.
    For example, a building might require [6, 6, 3] meaning the player must
    give one unit each of resources 6, 6, and 3.
    
    Attributes:
        resources (list[int]): List of required resource types/amounts.
                              Each element is a resource type (2-6) and
                              the position/count indicates quantity needed.
    """
    
    def __init__(self, resources: list[int]) -> None:
        """
        Initialize a CertainBuilding with specific resource requirements.
        
        Args:
            resources (list[int]): List of resource types required.
                                  Example: [6, 6, 3] requires three resources
                                  of types 6, 6, and 3 respectively.
        """
        super().__init__()
        self.resources = resources

    def is_able_to_buy(self, player_resources: Dict[int, int]) -> bool:
        """
        Check if a player has all required resources for this building.
        
        Verifies that the player has at least the specified quantity of
        each required resource type. Handles the case where a resource
        type is required multiple times (e.g., [6, 6, 3] needs 2x resource 6).
        
        Args:
            player_resources (Dict[int, int]): Player's resource inventory.
                                              Keys are resource types (2-6).
        
        Returns:
            bool: True if player has all required resources, False otherwise.
        """
        # Count how many of each resource type is needed
        resource_count = {}
        
        for resource in self.resources:
            # Get player's current count of this resource minus what we've
            # already allocated for this purchase
            if player_resources.get(resource, 0) - resource_count.get(resource, 0) - 1 < 0:
                # Player doesn't have enough of this resource
                return False
            # Track that we're using one of this resource
            resource_count[resource] = resource_count.get(resource, 0) + 1
        
        return True
    
    def name(self) -> str:
        """
        Return a descriptive name for this building.
        
        Returns:
            str: Description including building type and required resources.
        """
        return f"Normal Building {self.resources}"


class FlexBuilding(Building):
    """
    A Building with flexible resource requirements.
    
    Instead of requiring exact resources, this building requires a certain
    amount of resources that can be chosen from different types, with optional
    variety constraints. For example, a building might require 5 resources
    from at most 2 different types.
    
    Attributes:
        resources_require_count (int): Total number of resource units needed.
        variety (int | None): Maximum number of different resource types allowed.
                             None means no limit on variety.
    """
    
    def __init__(self, resources_require_count: int, variety: Optional[int] = None) -> None:
        """
        Initialize a FlexBuilding with flexible resource requirements.
        
        Args:
            resources_require_count (int): Total resources needed
                                          (or special value 7 for "any resource").
            variety (int | None): Maximum number of different resource types
                                 allowed in the purchase. None means unlimited.
        """
        super().__init__()
        self.resources_require_count = resources_require_count
        self.variety = variety

    def is_able_to_buy(self, player_resources: Dict[int, int]) -> bool:
        """
        Check if player has sufficient resources within variety constraints.
        
        Determines if a player can afford this flexible building. Requires
        the player to have enough total resources, with proper variety constraints.
        Special case: if resources_require_count == 7, any single resource
        with quantity > 0 is sufficient.
        
        Algorithm:
        1. If requirement is 7 (special), check if any resource exists
        2. Otherwise, sort resources by quantity (descending)
        3. Take top 'variety' resources and sum them
        4. Verify sum meets requirement AND all selected resources exist
        
        Args:
            player_resources (Dict[int, int]): Player's resource inventory.
        
        Returns:
            bool: True if player can afford this building, False otherwise.
        """
        # Special case: requirement of 7 means "any 1 resource of any type"
        if self.resources_require_count == 7:
            return any(v > 0 for key, v in player_resources.items() if key != 2)
        
        # Get the resource counts, sorted in descending order (most abundant first)
        counts = sorted((v for key,v in player_resources.items() if key != 2), reverse= True)
        
        # Sum the top 'variety' counts
        # If variety is None or more than available resources, take all
        total = sum(counts[:self.variety])
        
        # Check: have enough total AND all selected resources must exist (>0)
        # The second condition ensures we don't count zeros in our total
        return (total >= self.resources_require_count and 
                all(v > 0 for v in counts[:self.variety]))

    def name(self) -> str:
        """
        Return a descriptive name for this building.
        
        Returns:
            str: Description of required resource amount and variety.
        """
        return f"Building that needs {self.resources_require_count} resources of {self.variety} different types"