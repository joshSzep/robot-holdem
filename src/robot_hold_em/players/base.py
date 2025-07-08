"""
Base player implementation for Robot Hold 'Em poker game.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from rich.console import Console

from robot_hold_em.core import Card, GameState, PlayerAction

# Initialize Rich console for output
console = Console()


class Player(ABC):
    """Abstract base class for all players (human and robot)."""
    
    def __init__(self, player_id: str, name: str) -> None:
        """Initialize a player.
        
        Args:
            player_id: Unique identifier for the player
            name: Display name for the player
        """
        self.player_id = player_id
        self.name = name
    
    @abstractmethod
    def get_action(self, game_state: GameState) -> Tuple[PlayerAction, Optional[int]]:
        """Get the player's action for their turn.
        
        Args:
            game_state: Current state of the game
            
        Returns:
            A tuple containing the action and the bet amount (if applicable)
        """
        pass
    
    def notify_hole_cards(self, cards: List[Card]) -> None:
        """Notify the player of their hole cards.
        
        Args:
            cards: The player's hole cards
        """
        pass
    
    def notify_community_cards(self, cards: List[Card]) -> None:
        """Notify the player of the community cards.
        
        Args:
            cards: The community cards
        """
        pass
    
    def notify_game_result(self, winner_id: str, pot_amount: int) -> None:
        """Notify the player of the game result.
        
        Args:
            winner_id: ID of the winning player
            pot_amount: Amount of the pot
        """
        pass
    
    def __str__(self) -> str:
        """Return a string representation of the player."""
        return self.name





class RobotPlayer(Player, ABC):
    """Abstract base class for all robot players."""
    
    def __init__(self, player_id: str, name: str) -> None:
        """Initialize a robot player.
        
        Args:
            player_id: Unique identifier for the player
            name: Display name for the player
        """
        super().__init__(player_id, name)
        self.hole_cards: List[Card] = []
        self.community_cards: List[Card] = []
    
    def notify_hole_cards(self, cards: List[Card]) -> None:
        """Store the robot's hole cards.
        
        Args:
            cards: The robot's hole cards
        """
        self.hole_cards = cards
    
    def notify_community_cards(self, cards: List[Card]) -> None:
        """Store the community cards.
        
        Args:
            cards: The community cards
        """
        self.community_cards = cards
    
    @abstractmethod
    def get_action(self, game_state: GameState) -> Tuple[PlayerAction, Optional[int]]:
        """Get the robot's action based on its strategy.
        
        Args:
            game_state: Current state of the game
            
        Returns:
            A tuple containing the action and the bet amount (if applicable)
        """
        pass
