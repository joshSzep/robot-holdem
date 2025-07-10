"""
LLM-powered robot player implementation for Robot Hold 'Em.
"""

from typing import Dict, List, Optional, Tuple, Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

from robot_hold_em.core import Card, GameState, HandEvaluator, HandRank, PlayerAction
from robot_hold_em.players.base import RobotPlayer


class PokerAction(BaseModel):
    """Structured output schema for the LLM poker decision."""

    ACTION: str = Field(
        ...,
        description="The poker action to take (FOLD, CHECK, CALL, BET, or RAISE), including bet amount for BET/RAISE actions (e.g., 'BET $100')",
    )
    REASONING: str = Field(..., description="Explanation of why this action was chosen")


class LLMRobot(RobotPlayer):
    """A robot player powered by an LLM for decision making."""

    # Default personality for backward compatibility
    DEFAULT_PERSONALITY = "You are a strategic poker player who makes calculated decisions based on hand strength, position, and opponent behavior. You're willing to bluff occasionally but prefer solid mathematical plays."

    def __init__(
        self,
        player_id: str,
        name: str,
        model: str = "gpt-4o-mini",
        personality: Optional[str] = None,
    ):
        """Initialize the LLM robot player.

        Args:
            player_id: Unique identifier for the player
            name: Display name for the player
            model: The OpenAI model to use for decision making
            personality: A string describing the personality/style of play for this robot
                        (defaults to a strategic player if None)
        """
        super().__init__(player_id, name)
        self.model_name = model
        # Initialize PydanticAI OpenAIModel and Agent
        openai_model = OpenAIModel(self.model_name)
        self.agent = Agent(openai_model)
        self.decision_history: List[Dict[str, Any]] = []
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

    def _format_hand_rank(self, rank: HandRank, cards: List[Card]) -> str:
        """Format a hand rank for the LLM prompt.

        Args:
            rank: The hand rank
            cards: The cards that make up the hand

        Returns:
            A string description of the hand
        """
        return f"{rank.name} ({', '.join(self._format_card(card) for card in cards)})"

    def _create_game_state_description(self, game_state: GameState) -> str:
        """Create a description of the game state for the LLM.

        Args:
            game_state: Current state of the game

        Returns:
            A string describing the game state
        """
        # Get player's hole cards (already stored in self.hole_cards by notify_hole_cards)
        hole_cards_str = ", ".join(self._format_card(card) for card in self.hole_cards)

        # Get community cards (already stored in self.community_cards by notify_community_cards)
        community_cards_str = (
            "None"
            if not self.community_cards
            else ", ".join(self._format_card(card) for card in self.community_cards)
        )

        # Get player's position and stack
        # Calculate relative position based on dealer position
        player_ids = list(game_state.players.keys())
        dealer_pos = game_state.dealer_position
        player_pos = player_ids.index(self.player_id)

        # Calculate relative position (early, middle, late)
        num_players = len(player_ids)
        positions = ["Early", "Middle", "Late"]
        relative_pos = (player_pos - dealer_pos) % num_players
        position_index = min(2, (relative_pos * 3) // num_players)
        position = positions[position_index]

        player_state = game_state.players[self.player_id]
        stack = player_state.stack

        # Get current pot and bet information
        pot = game_state.current_pot
        current_highest_bet = max(p.current_bet for p in game_state.players.values())
        call_amount = current_highest_bet - player_state.current_bet

        # Determine betting round
        betting_round = "Preflop"
        if len(self.community_cards) == 3:
            betting_round = "Flop"
        elif len(self.community_cards) == 4:
            betting_round = "Turn"
        elif len(self.community_cards) == 5:
            betting_round = "River"

        # Evaluate current hand if possible
        hand_evaluation = ""
        if self.hole_cards:
            all_cards = self.hole_cards + self.community_cards
            if all_cards:
                rank, best_cards = HandEvaluator.evaluate(all_cards)
                hand_evaluation = (
                    f"Your current hand: {self._format_hand_rank(rank, best_cards)}"
                )

        # Create a mapping of player IDs to names
        player_names = {}

        # Try to get player names from the game object
        from robot_hold_em import PokerGame

        game_obj = None

        # Find the PokerGame instance that might be in the call stack
        import inspect

        for frame_info in inspect.stack():
            if "self" in frame_info.frame.f_locals:
                obj = frame_info.frame.f_locals["self"]
                if isinstance(obj, PokerGame):
                    game_obj = obj
                    break

        # If we found the game object, get player names
        if game_obj and hasattr(game_obj, "players"):
            for pid, player in game_obj.players.items():
                player_names[pid] = player.name
        else:
            # Default to player IDs if we can't get names
            for pid in game_state.players.keys():
                player_names[pid] = f"Player {pid}"

        # Get information about other players
        other_players = []
        for pid, p_state in game_state.players.items():
            if pid != self.player_id:
                player_name = player_names.get(pid, f"Player {pid}")
                status = "Folded" if p_state.folded else "Active"
                other_players.append(
                    f"{player_name}: Stack ${p_state.stack}, "
                    f"Current bet ${p_state.current_bet}, "
                    f"Status: {status}"
                )

        other_players_str = "\n".join(other_players)

        # Create the game state description
        description = f"""Current game state:
- Your hole cards: {hole_cards_str}
- Community cards: {community_cards_str}
- Your position: {position}
- Your stack: ${stack}
- Current pot: ${pot}
- Current highest bet: ${current_highest_bet}
- Amount to call: ${call_amount}
- Current betting round: {betting_round}

{hand_evaluation}

Other players:
{other_players_str}

Player name mapping (use these names in your reasoning instead of player IDs):
{", ".join([f"{name} (ID: {pid})" for pid, name in player_names.items() if pid != self.player_id])}
"""
        return description

    def _get_available_actions(
        self, game_state: GameState
    ) -> Dict[PlayerAction, Optional[int]]:
        """Determine the available actions for the current game state.

        Args:
            game_state: Current state of the game

        Returns:
            A dictionary mapping available actions to their default bet amounts
        """
        player_state = game_state.players[self.player_id]
        current_highest_bet = max(p.current_bet for p in game_state.players.values())
        call_amount = current_highest_bet - player_state.current_bet

        available_actions = {}

        # Can always fold
        available_actions[PlayerAction.FOLD] = None

        # Can check if no one has bet or we've already matched the highest bet
        if call_amount == 0:
            available_actions[PlayerAction.CHECK] = None

        # Can call if someone has bet and we have enough chips
        if call_amount > 0 and player_state.stack >= call_amount:
            available_actions[PlayerAction.CALL] = call_amount

        # Can bet or raise if we have chips left after calling
        if player_state.stack > call_amount:
            if call_amount == 0:
                # Default bet is 1x pot
                pot_size = sum(p.current_bet for p in game_state.players.values())
                default_bet = min(pot_size, player_state.stack)
                available_actions[PlayerAction.BET] = max(
                    game_state.big_blind, default_bet
                )
            else:
                # Default raise is 2x the current bet
                min_raise = call_amount + game_state.big_blind
                default_raise = min(current_highest_bet * 2, player_state.stack)
                available_actions[PlayerAction.RAISE] = max(min_raise, default_raise)

        return available_actions

    def _format_available_actions(
        self, available_actions: Dict[PlayerAction, Optional[int]]
    ) -> str:
        """Format the available actions for the LLM prompt.

        Args:
            available_actions: Dictionary of available actions and their default amounts

        Returns:
            A string description of the available actions
        """
        action_descriptions = []

        for action, amount in available_actions.items():
            if action == PlayerAction.FOLD:
                action_descriptions.append(
                    "FOLD - Give up your hand and forfeit any bets made so far"
                )
            elif action == PlayerAction.CHECK:
                action_descriptions.append(
                    "CHECK - Pass the action to the next player without betting"
                )
            elif action == PlayerAction.CALL:
                action_descriptions.append(f"CALL - Match the current bet of ${amount}")
            elif action == PlayerAction.BET:
                action_descriptions.append(
                    f"BET <amount> - Make a bet between ${amount // 2} and ${amount * 2}"
                )
            elif action == PlayerAction.RAISE:
                action_descriptions.append(
                    f"RAISE <amount> - Increase the bet to between ${amount // 2} and ${amount * 2}"
                )

        return "\n".join(action_descriptions)

    def _parse_llm_response(
        self, response: str, available_actions: Dict[PlayerAction, Optional[int]]
    ) -> Tuple[PlayerAction, Optional[int]]:
        """Parse the LLM's response to determine the action and bet amount.

        Args:
            response: The LLM's response or action string
            available_actions: Dictionary of available actions and their default amounts

        Returns:
            A tuple containing the action and the bet amount (if applicable)
        """
        import re

        # Extract the action and bet amount from the action string
        action_str = response.strip().upper()

        # Check for FOLD
        if "FOLD" in action_str:
            return PlayerAction.FOLD, None

        # Check for CHECK
        if "CHECK" in action_str and PlayerAction.CHECK in available_actions:
            return PlayerAction.CHECK, None

        # Check for CALL
        if "CALL" in action_str:
            # Even if CALL is not in available_actions, we may need to handle all-in
            player_state = self.game_state.players[self.player_id]
            current_highest_bet = max(p.current_bet for p in self.game_state.players.values())
            call_amount = current_highest_bet - player_state.current_bet
            
            # If player can't afford to call, but wants to call, they go all-in
            if call_amount > player_state.stack:
                return PlayerAction.CALL, player_state.stack  # All-in
            elif PlayerAction.CALL in available_actions:
                return PlayerAction.CALL, available_actions[PlayerAction.CALL]
            else:
                # If CALL is not available but the player tried to call, default to FOLD
                return PlayerAction.FOLD, None

        # Check for BET with amount
        bet_match = re.search(r"BET\s+\$?(\d+)", action_str)
        if bet_match and PlayerAction.BET in available_actions:
            bet_amount = int(bet_match.group(1))
            player_state = self.game_state.players[self.player_id]
            return PlayerAction.BET, min(bet_amount, player_state.stack)

        # Check for BET without amount
        if "BET" in action_str and PlayerAction.BET in available_actions:
            return PlayerAction.BET, available_actions[PlayerAction.BET]

        # Check for RAISE with amount
        raise_match = re.search(r"RAISE\s+\$?(\d+)", action_str)
        if raise_match and PlayerAction.RAISE in available_actions:
            raise_amount = int(raise_match.group(1))
            player_state = self.game_state.players[self.player_id]
            return PlayerAction.RAISE, min(raise_amount, player_state.stack)

        # Check for RAISE without amount
        if "RAISE" in action_str and PlayerAction.RAISE in available_actions:
            return PlayerAction.RAISE, available_actions[PlayerAction.RAISE]

        # Default to the safest option if we can't parse the response
        if PlayerAction.CHECK in available_actions:
            return PlayerAction.CHECK, None
        elif PlayerAction.CALL in available_actions:
            return PlayerAction.CALL, available_actions[PlayerAction.CALL]
        else:
            return PlayerAction.FOLD, None

    def get_action(self, game_state: GameState) -> Tuple[PlayerAction, Optional[int]]:
        """Choose an action using the LLM.

        Args:
            game_state: Current state of the game

        Returns:
            A tuple containing the action and the bet amount (if applicable)
        """
        # Store the game state for use in other methods
        self.game_state = game_state

        # Get available actions
        available_actions = self._get_available_actions(game_state)

        # Create the game state description
        game_state_description = self._create_game_state_description(game_state)

        # Format available actions
        actions_description = self._format_available_actions(available_actions)

        # Create the prompt for the LLM
        system_prompt = "You are a poker AI that makes strategic decisions."
        user_prompt = f"""
You are an AI poker player in a Texas Hold'em game. You need to make a decision based on the current game state.

{game_state_description}

Available actions:
{actions_description}

Your personality: {self.personality}

Respond with a JSON object containing your decision and reasoning in the following format:
{{"ACTION": "<action>", "REASONING": "<your reasoning>"}}

For the ACTION field, use ONLY ONE of the available actions listed above. For BET or RAISE, include the amount.
Example actions:
"FOLD"
"CHECK"
"CALL"
"BET $50"
"RAISE $100"

Your decision:
"""

        try:
            # Use the PydanticAI Agent to get a response
            # Combine system and user prompts since system parameter is not supported
            
            # Add a clear warning about stack limitations if the player can't call
            stack_warning = ""
            player_state = game_state.players[self.player_id]
            current_highest_bet = max(p.current_bet for p in game_state.players.values())
            call_amount = current_highest_bet - player_state.current_bet
            
            if call_amount > player_state.stack:
                stack_warning = f"\n\nIMPORTANT: You only have ${player_state.stack} in your stack, which is not enough to call the current bet of ${call_amount}. Your only options are to FOLD or go ALL-IN with your remaining ${player_state.stack}."
            
            combined_prompt = f"{system_prompt}\n\n{user_prompt}{stack_warning}"
            result = self.agent.run_sync(combined_prompt, output_type=PokerAction)

            # The result is an AgentRunResult object, and the PokerAction is in the output attribute
            from rich.console import Console
            from rich.panel import Panel

            console = Console()

            # Format hole cards and community cards for display
            hole_cards_str = ", ".join(
                self._format_card(card) for card in self.hole_cards
            )
            community_cards_str = (
                "None"
                if not self.community_cards
                else ", ".join(self._format_card(card) for card in self.community_cards)
            )

            # Get player's current stack and bet information
            player_state = game_state.players[self.player_id]
            stack = player_state.stack
            current_bet = player_state.current_bet
            
            # Calculate the amount needed to call
            current_highest_bet = max(
                p.current_bet for p in game_state.players.values()
            )
            to_raise = current_highest_bet - current_bet

            # Display the AI's thought process with the player's name and additional context
            console.print(
                Panel(
                    f"[bold cyan]{self.name}'s Thought Process:[/bold cyan]\n"
                    + f"[yellow]Hole Cards:[/yellow] {hole_cards_str}\n"
                    + f"[yellow]Community Cards:[/yellow] {community_cards_str}\n"
                    + f"[yellow]Current Stack:[/yellow] ${stack:,}\n"
                    + f"[yellow]Current Bet:[/yellow] ${current_bet:,}\n"
                    + f"[yellow]To Call:[/yellow] ${to_raise:,}\n\n"
                    + f"[italic]Action: {result.output.ACTION}\n\nReasoning: {result.output.REASONING}[/italic]",
                    border_style="cyan",
                    title="AI Poker Thoughts",
                )
            )

            # Parse the LLM's response using the PokerAction object directly
            action, bet_amount = self._parse_llm_response(
                result.output.ACTION,  # Use the ACTION field from the PokerAction object in result.output
                available_actions,
            )

            # Store the decision for history
            self.decision_history.append(
                {
                    "game_state": game_state_description,
                    "available_actions": actions_description,
                    "llm_response": result.output,
                    "parsed_action": action.name,
                    "bet_amount": bet_amount,
                }
            )

            return action, bet_amount

        except Exception as e:
            # If there's an error with the LLM, fall back to a simple strategy
            print(f"Error using LLM for decision: {e}")

            # Simple fallback strategy
            player_state = game_state.players[self.player_id]
            current_highest_bet = max(
                p.current_bet for p in game_state.players.values()
            )
            call_amount = current_highest_bet - player_state.current_bet

            if call_amount == 0:
                return PlayerAction.CHECK, None
            elif call_amount <= game_state.big_blind * 2:
                return PlayerAction.CALL, call_amount
            else:
                return PlayerAction.FOLD, None
