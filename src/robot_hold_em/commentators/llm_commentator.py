"""
LLM-powered commentator implementation for Robot Hold 'Em.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

from robot_hold_em.commentators.base import Commentator, GameEvent
from robot_hold_em.core import Card, PlayerAction


class CommentaryOutput(BaseModel):
    """Structured output schema for the LLM commentary."""

    COMMENTARY: str = Field(
        ...,
        description="The commentary text for the current poker game situation",
    )


class LLMCommentator(Commentator):
    """A commentator powered by an LLM for generating commentary."""

    # Default personality
    DEFAULT_PERSONALITY = "You are an enthusiastic poker commentator who provides insightful and entertaining commentary on poker games. You focus on strategy, player psychology, and dramatic moments."

    def __init__(
        self,
        commentator_id: str,
        name: str,
        model: str = "gpt-4o-mini",
        personality: Optional[str] = None,
    ):
        """Initialize the LLM commentator.

        Args:
            commentator_id: Unique identifier for the commentator
            name: Display name for the commentator
            model: The OpenAI model to use for commentary generation
            personality: A string describing the personality/style of the commentator
                        (defaults to an enthusiastic commentator if None)
        """
        super().__init__(commentator_id, name)
        self.model_name = model
        # Initialize PydanticAI OpenAIModel and Agent
        openai_model = OpenAIModel(self.model_name)
        self.agent = Agent(openai_model)
        self.personality = (
            personality if personality is not None else self.DEFAULT_PERSONALITY
        )

    def _format_card(self, card: Card) -> str:
        """Format a card for the LLM prompt.

        Args:
            card: The card to format

        Returns:
            A string representation of the card
        """
        return f"{card.rank.name} of {card.suit.name}"

    def _create_game_state_description(self, event: GameEvent) -> str:
        """Create a description of the game state for the LLM.

        Args:
            event: The game event to comment on

        Returns:
            A string describing the game state
        """
        game_state = event.game_state
        player_names = event.player_names

        # Describe the community cards
        community_cards_str = (
            "None"
            if not game_state.community_cards
            else ", ".join(
                self._format_card(card) for card in game_state.community_cards
            )
        )

        # Describe the pot
        pot_str = f"${game_state.current_pot:,}"

        # Describe the players
        players_info = []
        for player_id, player_state in game_state.players.items():
            status = "folded" if player_state.folded else "active"
            if player_state.all_in:
                status = "all-in"

            # Get player name or fall back to ID if not available
            player_name = player_names.get(player_id, f"Player {player_id}")

            # Don't include hole cards in the description (commentators don't see them)
            players_info.append(
                f"{player_name}: {status}, stack: ${player_state.stack:,}, bet: ${player_state.current_bet:,}"
            )

        players_str = "\n".join(players_info)

        # Describe the current betting round
        round_str = str(game_state.betting_round)

        # Combine all information
        return f"""
Current Betting Round: {round_str}
Community Cards: {community_cards_str}
Current Pot: {pot_str}
Players:
{players_str}
"""

    def _create_event_description(self, event: GameEvent) -> str:
        """Create a description of the event for the LLM.

        Args:
            event: The game event to describe

        Returns:
            A string describing the event
        """
        player_names = event.player_names
        
        if event.event_type == GameEvent.EventType.GAME_START:
            return "The poker game is starting. Players are taking their seats."

        elif event.event_type == GameEvent.EventType.HAND_START:
            return "A new hand is being dealt."

        elif event.event_type == GameEvent.EventType.BLINDS_POSTED:
            # Get small and big blind player names if available
            small_blind_id = event.additional_info.get("small_blind_id")
            big_blind_id = event.additional_info.get("big_blind_id")
            
            small_blind_name = player_names.get(small_blind_id, f"Player {small_blind_id}") if small_blind_id else "Small blind"
            big_blind_name = player_names.get(big_blind_id, f"Player {big_blind_id}") if big_blind_id else "Big blind"
            
            return f"The blinds have been posted. {small_blind_name} posted the small blind and {big_blind_name} posted the big blind."

        elif event.event_type == GameEvent.EventType.HOLE_CARDS_DEALT:
            return "The hole cards have been dealt to each player."

        elif event.event_type == GameEvent.EventType.PLAYER_ACTION:
            # Get player name or fall back to ID if not available
            player_name = player_names.get(event.player_id, f"Player {event.player_id}")
            action_str = str(event.action)

            if event.action in [PlayerAction.BET, PlayerAction.RAISE]:
                return f"{player_name} has decided to {action_str.lower()} ${event.bet_amount:,}."
            elif event.action == PlayerAction.CALL:
                return f"{player_name} has called."
            elif event.action == PlayerAction.CHECK:
                return f"{player_name} has checked."
            elif event.action == PlayerAction.FOLD:
                return f"{player_name} has folded."
            elif event.action == PlayerAction.ALL_IN:
                return f"{player_name} has gone all-in with ${event.bet_amount:,}!"

        elif event.event_type == GameEvent.EventType.FLOP_DEALT:
            cards_str = ", ".join(
                self._format_card(card) for card in event.game_state.community_cards[:3]
            )
            return f"The flop has been dealt: {cards_str}."

        elif event.event_type == GameEvent.EventType.TURN_DEALT:
            turn_card = event.game_state.community_cards[3]
            return f"The turn card is the {self._format_card(turn_card)}."

        elif event.event_type == GameEvent.EventType.RIVER_DEALT:
            river_card = event.game_state.community_cards[4]
            return f"The river card is the {self._format_card(river_card)}."

        elif event.event_type == GameEvent.EventType.SHOWDOWN:
            return "We've reached the showdown. Players will now reveal their hands."

        elif event.event_type == GameEvent.EventType.WINNER_DETERMINED:
            # Get winner name or fall back to ID if not available
            winner_name = player_names.get(event.winner_id, f"Player {event.winner_id}")
            return f"{winner_name} has won the pot of ${event.pot_amount:,}."

        elif event.event_type == GameEvent.EventType.HAND_END:
            return "The hand has ended."

        elif event.event_type == GameEvent.EventType.GAME_END:
            return "The poker game has concluded."

        return f"Event: {event.event_type}"

    def generate_commentary(self, event: GameEvent) -> Optional[str]:
        """Generate commentary for a game event using the LLM.

        Args:
            event: The game event to comment on

        Returns:
            Commentary text, or None if no commentary is generated
        """
        # Create descriptions of the game state and event
        game_state_description = self._create_game_state_description(event)
        event_description = self._create_event_description(event)

        # Create the prompt for the LLM
        system_prompt = f"""
You are {self.name}, a poker commentator with the following personality:
{self.personality}

You are providing live commentary for a Texas Hold'em poker game. 
Your commentary should be engaging, insightful, and reflect your personality.
Focus on the current situation and what just happened, not on predicting future actions.
Keep your commentary concise (1-3 sentences) and conversational.
"""

        user_prompt = f"""
Game State:
{game_state_description}

Event:
{event_description}

Provide a brief commentary on this situation that matches your personality.
"""

        try:
            # Use the PydanticAI Agent to get a response
            combined_prompt = f"{system_prompt}\n\n{user_prompt}"
            result = self.agent.run_sync(combined_prompt, output_type=CommentaryOutput)

            # Return the commentary
            return result.output.COMMENTARY

        except Exception as e:
            print(f"Error generating commentary: {e}")
            return None
