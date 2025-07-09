"""
Commentator manager for Robot Hold 'Em poker game.
"""

import random
from typing import Dict, Optional

from rich.console import Console
from rich.panel import Panel

from robot_hold_em.commentators.base import Commentator, GameEvent


class CommentatorManager:
    """Manages multiple commentators and decides when to trigger commentary."""
    
    def __init__(self, console: Console, commentary_frequency: float = 0.7):
        """Initialize the commentator manager.
        
        Args:
            console: Rich console for displaying commentary
            commentary_frequency: Probability (0-1) of generating commentary for an event
        """
        self.commentators: Dict[str, Commentator] = {}
        self.console = console
        self.commentary_frequency = max(0.0, min(1.0, commentary_frequency))
        self.active_commentator: Optional[str] = None
        
        # Configure event type weights (higher = more likely to trigger commentary)
        self.event_weights = {
            GameEvent.EventType.GAME_START: 1.0,
            GameEvent.EventType.HAND_START: 0.5,
            GameEvent.EventType.BLINDS_POSTED: 0.2,
            GameEvent.EventType.HOLE_CARDS_DEALT: 0.3,
            GameEvent.EventType.PLAYER_ACTION: 0.8,
            GameEvent.EventType.FLOP_DEALT: 0.9,
            GameEvent.EventType.TURN_DEALT: 0.9,
            GameEvent.EventType.RIVER_DEALT: 0.9,
            GameEvent.EventType.SHOWDOWN: 1.0,
            GameEvent.EventType.WINNER_DETERMINED: 1.0,
            GameEvent.EventType.HAND_END: 0.7,
            GameEvent.EventType.GAME_END: 1.0,
        }
    
    def add_commentator(self, commentator: Commentator) -> None:
        """Add a commentator to the manager.
        
        Args:
            commentator: The commentator to add
        """
        self.commentators[commentator.commentator_id] = commentator
        
        # Set as active commentator if it's the first one
        if self.active_commentator is None:
            self.active_commentator = commentator.commentator_id
    
    def set_active_commentator(self, commentator_id: str) -> None:
        """Set the active commentator.
        
        Args:
            commentator_id: ID of the commentator to set as active
            
        Raises:
            ValueError: If the commentator ID is not found
        """
        if commentator_id not in self.commentators:
            raise ValueError(f"Commentator with ID {commentator_id} not found")
        self.active_commentator = commentator_id
    
    def select_random_commentator(self) -> None:
        """Randomly select an active commentator."""
        if self.commentators:
            self.active_commentator = random.choice(list(self.commentators.keys()))
    
    def handle_event(self, event: GameEvent) -> None:
        """Handle a game event and potentially generate commentary.
        
        Args:
            event: The game event to handle
        """
        # Check if we should generate commentary based on frequency and event type
        event_weight = self.event_weights.get(event.event_type, 0.5)
        if random.random() > (self.commentary_frequency * event_weight):
            return
        
        # Randomly select a commentator for this event
        self.select_random_commentator()
        
        if self.active_commentator:
            commentator = self.commentators[self.active_commentator]
            commentary = commentator.generate_commentary(event)
            
            if commentary:
                # Display the commentary
                self.console.print()
                self.console.print(
                    Panel(
                        f"[italic]{commentary}[/italic]",
                        border_style="bright_blue",
                        title=f"[bold]{commentator.name}[/bold]",
                        title_align="left",
                    )
                )
                self.console.print()
