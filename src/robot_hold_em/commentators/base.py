"""
Base commentator class for Robot Hold 'Em poker game.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Mapping

from robot_hold_em.core import GameState, PlayerAction


class GameEvent:
    """Represents a game event that can trigger commentary."""
    
    class EventType:
        """Enum-like class for event types."""
        GAME_START = "game_start"
        HAND_START = "hand_start"
        BLINDS_POSTED = "blinds_posted"
        HOLE_CARDS_DEALT = "hole_cards_dealt"
        PLAYER_ACTION = "player_action"
        FLOP_DEALT = "flop_dealt"
        TURN_DEALT = "turn_dealt"
        RIVER_DEALT = "river_dealt"
        SHOWDOWN = "showdown"
        WINNER_DETERMINED = "winner_determined"
        HAND_END = "hand_end"
        GAME_END = "game_end"
    
    def __init__(
        self, 
        event_type: str, 
        game_state: GameState,
        player_id: Optional[str] = None,
        action: Optional[PlayerAction] = None,
        bet_amount: Optional[int] = None,
        winner_id: Optional[str] = None,
        pot_amount: Optional[int] = None,
        additional_info: Optional[Dict] = None,
        player_names: Optional[Mapping[str, str]] = None
    ):
        """Initialize a game event.
        
        Args:
            event_type: Type of the event
            game_state: Current state of the game
            player_id: ID of the player involved in the event (if applicable)
            action: Player action (if applicable)
            bet_amount: Amount bet (if applicable)
            winner_id: ID of the winner (if applicable)
            pot_amount: Amount in the pot (if applicable)
            additional_info: Any additional information about the event
            player_names: Mapping of player IDs to their display names (if applicable)
        """
        self.event_type = event_type
        self.game_state = game_state
        self.player_id = player_id
        self.action = action
        self.bet_amount = bet_amount
        self.winner_id = winner_id
        self.pot_amount = pot_amount
        self.additional_info = additional_info or {}
        self.player_names = player_names or {}


class Commentator(ABC):
    """Base class for poker game commentators."""
    
    def __init__(self, commentator_id: str, name: str):
        """Initialize a commentator.
        
        Args:
            commentator_id: Unique identifier for the commentator
            name: Display name for the commentator
        """
        self.commentator_id = commentator_id
        self.name = name
    
    @abstractmethod
    def generate_commentary(self, event: GameEvent) -> Optional[str]:
        """Generate commentary for a game event.
        
        Args:
            event: The game event to comment on
            
        Returns:
            Commentary text, or None if no commentary is generated
        """
        pass
