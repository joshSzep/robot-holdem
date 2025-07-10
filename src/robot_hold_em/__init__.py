"""
Robot Hold 'Em - A Texas Hold 'Em poker game with robot opponents.
"""

from typing import Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from robot_hold_em.settings import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    STARTING_STACK,
    SMALL_BLIND,
    BIG_BLIND,
    BROADCAST_MODE,
    NUM_HANDS,
)

from robot_hold_em.core import (
    Card,
    GameState,
    HandEvaluator,
    HandComparator,
    PlayerAction,
)
from robot_hold_em.players import Player
from robot_hold_em.players.llm_personalities import LLMPersonalities
from robot_hold_em.commentators import CommentatorManager, GameEvent
from robot_hold_em.commentators.personalities import CommentatorPersonalities

# Initialize Rich console
console = Console()


def display_hand(cards: List[Card], name: str) -> None:
    """Display a player's hand and its evaluation."""
    hand_str = " ".join(str(card) for card in cards)
    rank, best_cards = HandEvaluator.evaluate(cards)
    best_hand_str = " ".join(str(card) for card in best_cards)

    table = Table(show_header=False, box=box.SIMPLE)
    table.add_column("Player", style="bold cyan")
    table.add_column("Hand", style="white")

    table.add_row(f"{name}'s hand:", hand_str)
    table.add_row("Best hand:", f"[bold]{rank}[/bold] - {best_hand_str}")

    console.print(table)


def format_chips(amount: int) -> str:
    """Format chip amount with commas and dollar sign."""
    return f"${amount:,}"


def print_header(text: str) -> None:
    """Print a formatted header."""
    console.print(f"\n[bold white on blue]{text}[/bold white on blue]")


def print_section(text: str) -> None:
    """Print a formatted section header."""
    console.print(f"\n[bold cyan]--- {text} ---[/bold cyan]")


def print_winner(text: str) -> None:
    """Print a formatted winner announcement."""
    console.print(Panel(f"[bold green]{text}[/bold green]", border_style="green"))


class PokerGame:
    """Main game controller for Robot Hold 'Em."""

    def __init__(
        self,
        starting_stack: int = 1000,
        small_blind: int = 5,
        big_blind: int = 10,
        broadcast_mode: bool = False,
        enable_commentary: bool = True,
        commentary_frequency: float = 0.7,
    ) -> None:
        """Initialize the poker game.

        Args:
            starting_stack: Amount of chips each player starts with
            small_blind: Amount of the small blind
            big_blind: Amount of the big blind
            broadcast_mode: If True, shows all players' hole cards and detailed commentary
            enable_commentary: If True, enables commentator commentary during the game
            commentary_frequency: Probability (0-1) of generating commentary for an event
        """
        self.starting_stack = starting_stack
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.players: Dict[str, Player] = {}
        self.game_state: Optional[GameState] = None
        self.broadcast_mode = broadcast_mode
        self.enable_commentary = enable_commentary
        self.commentator_manager = CommentatorManager(console, commentary_frequency) if enable_commentary else None

    def add_player(self, player: Player) -> None:
        """Add a player to the game.

        Args:
            player: The player to add
        """
        self.players[player.player_id] = player
        
    def _get_player_names_mapping(self) -> Dict[str, str]:
        """Create a mapping of player IDs to their display names.
        
        Returns:
            Dictionary mapping player IDs to display names
        """
        return {player_id: player.name for player_id, player in self.players.items()}
        
    def add_commentator(self, commentator_id: str, name: str, personality_type: str = "professional", model: str = "gpt-4o-mini") -> None:
        """Add a commentator to the game.
        
        Args:
            commentator_id: Unique identifier for the commentator
            name: Display name for the commentator
            personality_type: Type of personality to use
            model: The OpenAI model to use for commentary generation
        """
        if not self.enable_commentary or not self.commentator_manager:
            return
            
        commentator = CommentatorPersonalities.create_commentator(
            commentator_id, name, personality_type, model
        )
        self.commentator_manager.add_commentator(commentator)

    def setup_game(self) -> None:
        """Set up the game state with the current players."""
        player_ids = list(self.players.keys())
        self.game_state = GameState(
            player_ids, self.starting_stack, self.small_blind, self.big_blind
        )
        
        # Emit game start event
        if self.enable_commentary and self.commentator_manager and self.game_state:
            event = GameEvent(
                event_type=GameEvent.EventType.GAME_START,
                game_state=self.game_state,
                player_names=self._get_player_names_mapping()
            )
            self.commentator_manager.handle_event(event)

    def play_hand(self) -> None:
        """Play a single hand of poker."""
        if not self.game_state:
            raise ValueError("Game state not initialized. Call setup_game() first.")

        # Start a new hand
        self.game_state.reset_for_new_hand()

        console.rule(style="bright_blue")
        print_header("NEW HAND")
        console.print(
            f"Blinds: Small [green]{format_chips(self.game_state.small_blind)}[/green], Big [green]{format_chips(self.game_state.big_blind)}[/green]"
        )

        dealer_id = list(self.players.keys())[self.game_state.dealer_position]
        print(f"Dealer: {self.players[dealer_id].name}")
        
        # Emit hand start event
        if self.enable_commentary and self.commentator_manager:
            event = GameEvent(
                event_type=GameEvent.EventType.HAND_START,
                game_state=self.game_state,
                player_names=self._get_player_names_mapping()
            )
            self.commentator_manager.handle_event(event)

        # Post blinds
        small_blind_pos = (self.game_state.dealer_position + 1) % len(self.players)
        big_blind_pos = (self.game_state.dealer_position + 2) % len(self.players)
        small_blind_id = list(self.players.keys())[small_blind_pos]
        big_blind_id = list(self.players.keys())[big_blind_pos]

        self._place_bet(small_blind_id, self.game_state.small_blind)
        self._place_bet(big_blind_id, self.game_state.big_blind)

        print(
            f"Small blind: {self.players[small_blind_id].name} ({format_chips(self.game_state.small_blind)})"
        )
        print(
            f"Big blind: {self.players[big_blind_id].name} ({format_chips(self.game_state.big_blind)})"
        )
        
        # Emit blinds posted event
        if self.enable_commentary and self.commentator_manager:
            event = GameEvent(
                event_type=GameEvent.EventType.BLINDS_POSTED,
                game_state=self.game_state,
                additional_info={
                    "small_blind_id": small_blind_id,
                    "big_blind_id": big_blind_id
                },
                player_names=self._get_player_names_mapping()
            )
            self.commentator_manager.handle_event(event)

        # Notify players of their hole cards
        print_section("HOLE CARDS")

        # Create a table for hole cards
        table = Table(box=box.SIMPLE)
        table.add_column("Player", style="bold")
        # Deal hole cards to each player
        self.game_state._deal_hole_cards()

        # Notify each player of their hole cards
        for player_id, player in self.players.items():
            player.notify_hole_cards(self.game_state.players[player_id].hole_cards)
            
        # Emit hole cards dealt event
        if self.enable_commentary and self.commentator_manager:
            event = GameEvent(
                event_type=GameEvent.EventType.HOLE_CARDS_DEALT,
                game_state=self.game_state,
                player_names=self._get_player_names_mapping()
            )
            self.commentator_manager.handle_event(event)

        # Show all robot players' cards in broadcast mode
        if self.broadcast_mode:
            for player_id, player in self.players.items():
                player_state = self.game_state.players[player_id]
                cards_str = f"{player_state.hole_cards[0]} {player_state.hole_cards[1]}"
                stack_str = format_chips(player_state.stack)
                table.add_row(player.name, cards_str, stack_str)

        # Print the table in broadcast mode
        if self.broadcast_mode:
            console.print(table)

        # Play betting rounds
        self._play_betting_round("Preflop")

        # If more than one player is still in the hand, continue to the flop
        if self._count_active_players() > 1:
            flop_cards = self.game_state.deal_flop()
            print_section("FLOP")
            console.print(" ".join(str(card) for card in flop_cards))

            # Notify each player of the community cards
            for player_id, player in self.players.items():
                player.notify_community_cards(self.game_state.community_cards)
                
            # Emit flop dealt event
            if self.enable_commentary and self.commentator_manager:
                event = GameEvent(
                    event_type=GameEvent.EventType.FLOP_DEALT,
                    game_state=self.game_state,
                    player_names=self._get_player_names_mapping()
                )
                self.commentator_manager.handle_event(event)

            self._play_betting_round("Flop")

        # If more than one player is still in the hand, continue to the turn
        if self._count_active_players() > 1:
            turn_card = self.game_state.deal_turn()
            print_section("TURN")
            console.print(str(turn_card))

            # Notify each player of the updated community cards
            for player_id, player in self.players.items():
                player.notify_community_cards(self.game_state.community_cards)
                
            # Emit turn dealt event
            if self.enable_commentary and self.commentator_manager:
                event = GameEvent(
                    event_type=GameEvent.EventType.TURN_DEALT,
                    game_state=self.game_state,
                    player_names=self._get_player_names_mapping()
                )
                self.commentator_manager.handle_event(event)

            self._play_betting_round("Turn")

        # If more than one player is still in the hand, continue to the river
        if self._count_active_players() > 1:
            river_card = self.game_state.deal_river()
            print_section("RIVER")
            console.print(str(river_card))

            # Notify each player of the updated community cards
            for player_id, player in self.players.items():
                player.notify_community_cards(self.game_state.community_cards)
                
            # Emit river dealt event
            if self.enable_commentary and self.commentator_manager:
                event = GameEvent(
                    event_type=GameEvent.EventType.RIVER_DEALT,
                    game_state=self.game_state,
                    player_names=self._get_player_names_mapping()
                )
                self.commentator_manager.handle_event(event)

            self._play_betting_round("River")

        # Show all community cards
        if self.game_state.community_cards:
            community_str = " ".join(
                str(card) for card in self.game_state.community_cards
            )
            console.print(f"\nCommunity cards: [bold red]{community_str}[/bold red]")

        # Showdown if more than one player is still in the hand
        if self._count_active_players() > 1:
            # Emit showdown event
            if self.enable_commentary and self.commentator_manager:
                event = GameEvent(
                    event_type=GameEvent.EventType.SHOWDOWN,
                    game_state=self.game_state,
                    player_names=self._get_player_names_mapping()
                )
                self.commentator_manager.handle_event(event)
            
            self._showdown()
        else:
            # Only one player left, they win by default
            for player_id, player_state in self.game_state.players.items():
                if not player_state.folded:
                    winner_name = self.players[player_id].name
                    print(
                        f"\n--- {winner_name} wins ${self.game_state.current_pot} by default (all others folded) ---"
                    )
                    # Update the winner's stack with the pot amount
                    player_state.stack += self.game_state.current_pot
                    
                    # Show updated stack in broadcast mode
                    if self.broadcast_mode:
                        console.print(
                            f"{winner_name}'s updated stack: [bold green]{format_chips(player_state.stack)}[/bold green]"
                        )
                    
                    # Emit winner determined event
                    if self.enable_commentary and self.commentator_manager:
                        event = GameEvent(
                            event_type=GameEvent.EventType.WINNER_DETERMINED,
                            game_state=self.game_state,
                            winner_id=player_id,
                            pot_amount=self.game_state.current_pot,
                            player_names=self._get_player_names_mapping()
                        )
                        self.commentator_manager.handle_event(event)
                    break

    def _count_active_players(self) -> int:
        """Count the number of players still in the hand.

        Returns:
            Number of active (non-folded) players with chips
        """
        if not self.game_state:
            return 0

        count = 0
        for player_state in self.game_state.players.values():
            if not player_state.folded and player_state.stack > 0:
                count += 1
        return count

    def _play_betting_round(self, round_name: str) -> None:
        """Play a betting round.

        Args:
            round_name: Name of the betting round for display
        """
        if not self.game_state:
            return

        print_section(f"{round_name.upper()} BETTING")

        # Get the proper betting order
        player_ids = list(self.players.keys())

        # For preflop, betting starts with the player after the big blind (UTG position)
        # For all other rounds, betting starts with the player after the dealer (small blind position)
        if round_name.lower() == "preflop":
            # Start with the player after the big blind
            start_pos = (self.game_state.dealer_position + 3) % len(player_ids)
        else:
            # Start with the player after the dealer/button
            start_pos = (self.game_state.dealer_position + 1) % len(player_ids)

        ordered_player_ids = player_ids[start_pos:] + player_ids[:start_pos]

        # Track the highest bet for commentary
        highest_bet = max(p.current_bet for p in self.game_state.players.values())

        # Track which players need to act
        active_players = [
            pid
            for pid in ordered_player_ids
            if not self.game_state.players[pid].folded
            and not self.game_state.players[pid].all_in
            and self.game_state.players[pid].stack > 0  # Skip players with zero chips
        ]

        # Keep track of who has acted since the last bet/raise

        # Keep track of players who have acted since the last raise
        players_acted_since_raise = set()

        # Continue betting until all active players have called or folded
        current_player_index = 0

        while active_players and current_player_index < len(active_players):
            player_id = active_players[current_player_index]
            player = self.players[player_id]
            player_state = self.game_state.players[player_id]

            # Get the current highest bet
            current_highest_bet = max(
                p.current_bet for p in self.game_state.players.values()
            )
            call_amount = current_highest_bet - player_state.current_bet

            # Get player's action
            action, bet_amount = player.get_action(self.game_state)
            player_state.last_action = action

            # Process the action with ESPN-style commentary
            player_name = f"[bold]{player.name}[/bold]"
            if action == PlayerAction.FOLD:
                player_state.folded = True
                if call_amount > 0:
                    console.print(
                        f"{player_name} [yellow]folds[/yellow] to the [green]{format_chips(call_amount)}[/green] bet"
                    )
                else:
                    console.print(f"{player_name} [yellow]folds[/yellow]")

                # Remove folded player from active players
                active_players.remove(player_id)
                current_player_index -= 1  # Adjust index since we removed a player

            elif action == PlayerAction.CHECK:
                console.print(f"{player_name} [blue]checks[/blue]")
                players_acted_since_raise.add(player_id)

            elif action == PlayerAction.CALL:
                if bet_amount is not None:
                    self._place_bet(player_id, bet_amount)
                    if bet_amount > 0:
                        console.print(
                            f"{player_name} [cyan]calls[/cyan] [green]{format_chips(bet_amount)}[/green]"
                        )
                    else:
                        console.print(f"{player_name} [blue]checks[/blue]")
                    players_acted_since_raise.add(player_id)

            elif action == PlayerAction.BET:
                if bet_amount is not None:
                    self._place_bet(player_id, bet_amount)
                    console.print(
                        f"{player_name} [magenta]bets[/magenta] [green]{format_chips(bet_amount)}[/green]"
                    )
                    highest_bet = player_state.current_bet

                    # Reset the list of players who have acted since the last raise
                    players_acted_since_raise = {player_id}

            elif action == PlayerAction.RAISE:
                if bet_amount is not None:
                    prev_bet = highest_bet
                    self._place_bet(player_id, bet_amount)
                    raise_to = player_state.current_bet
                    raise_amount = raise_to - prev_bet
                    console.print(
                        f"{player_name} [red]raises[/red] [green]{format_chips(raise_amount)}[/green] to [green]{format_chips(raise_to)}[/green]"
                    )
                    highest_bet = raise_to

                    # Reset the list of players who have acted since the last raise
                    players_acted_since_raise = {player_id}

            # Display stack information in broadcast mode
            if self.broadcast_mode:
                console.print(
                    f"  {player.name}'s stack: [green]{format_chips(player_state.stack)}[/green]"
                )

            # Check if player went all-in
            if player_state.all_in and player_id in active_players:
                active_players.remove(player_id)
                current_player_index -= 1  # Adjust index since we removed a player

            # Check if betting round is over (only one player left)
            if self._count_active_players() <= 1:
                break

            # Move to the next player
            current_player_index += 1

            # If we've gone through all players, check if we need another round
            if current_player_index >= len(active_players):
                # If all active players have acted since the last raise, betting is done
                if set(active_players).issubset(players_acted_since_raise):
                    break
                else:
                    # Start another round of betting from the beginning
                    current_player_index = 0

            # Emit player action event
            if self.enable_commentary and self.commentator_manager:
                event = GameEvent(
                    event_type=GameEvent.EventType.PLAYER_ACTION,
                    game_state=self.game_state,
                    player_id=player_id,
                    action=action,
                    bet_amount=bet_amount if action in [PlayerAction.BET, PlayerAction.RAISE] else None,
                    player_names=self._get_player_names_mapping()
                )
                self.commentator_manager.handle_event(event)

    def _place_bet(self, player_id: str, amount: int) -> None:
        """Place a bet for a player.

        Args:
            player_id: ID of the player placing the bet
            amount: Amount to bet
        """
        if not self.game_state:
            return

        player_state = self.game_state.players[player_id]

        # Cap the bet at the player's stack (all-in)
        actual_amount = min(amount, player_state.stack)

        player_state.stack -= actual_amount
        player_state.current_bet += actual_amount
        self.game_state.current_pot += actual_amount

        # Check if player is all-in
        if player_state.stack == 0:
            player_state.all_in = True

    def _showdown(self) -> None:
        """Evaluate hands and determine the winner."""
        if not self.game_state:
            return

        print_section("SHOWDOWN")

        player_hands = {}

        # Evaluate each player's hand
        for player_id, player_state in self.game_state.players.items():
            if not player_state.folded:
                player = self.players[player_id]
                hand = self.game_state.get_player_hand(player_id)
                display_hand(hand, player.name)

                # Store hand evaluation for later comparison
                rank, best_cards = HandEvaluator.evaluate(hand)
                player_hands[player_id] = (rank, best_cards, hand)

        # Find the best hand(s) using proper comparison
        winners = []
        best_player_id = None

        # Compare each player's hand against the current best hand
        for player_id, (rank, best_cards, full_hand) in player_hands.items():
            if not winners:  # First player we're evaluating
                winners = [player_id]
                best_player_id = player_id
            else:
                # Compare this hand with the current best hand
                comparison = HandComparator.compare_hands(
                    full_hand, player_hands[best_player_id][2]
                )

                if comparison > 0:  # This hand is better
                    winners = [player_id]
                    best_player_id = player_id
                elif comparison == 0:  # This hand is equal
                    winners.append(player_id)

        # Announce the winner(s) with ESPN-style commentary
        pot_share = self.game_state.current_pot // len(winners)

        console.rule(style="green")
        if len(winners) == 1:
            winner_id = winners[0]
            winner_name = self.players[winner_id].name
            winner_rank, winner_cards, _ = player_hands[winner_id]

            win_message = (
                f"{winner_name} WINS {format_chips(pot_share)} WITH {winner_rank}"
            )
            print_winner(win_message)

            # Update player's stack
            self.game_state.players[winner_id].stack += pot_share

            # Show updated stack in broadcast mode
            if self.broadcast_mode:
                console.print(
                    f"{winner_name}'s updated stack: [bold green]{format_chips(self.game_state.players[winner_id].stack)}[/bold green]"
                )
                
            # Emit winner determined event
            if self.enable_commentary and self.commentator_manager:
                event = GameEvent(
                    event_type=GameEvent.EventType.WINNER_DETERMINED,
                    game_state=self.game_state,
                    winner_id=winner_id,
                    pot_amount=self.game_state.current_pot,
                    player_names=self._get_player_names_mapping()
                )
                self.commentator_manager.handle_event(event)
        else:
            split_message = f"SPLIT POT: {format_chips(pot_share)} EACH"
            print_winner(split_message)

            for winner_id in winners:
                winner_name = self.players[winner_id].name
                winner_rank, _, _ = player_hands[winner_id]
                console.print(
                    f"[bold]{winner_name}[/bold] wins with [cyan]{winner_rank}[/cyan]"
                )

                # Update player's stack
                self.game_state.players[winner_id].stack += pot_share

                # Show updated stack in broadcast mode
                if self.broadcast_mode:
                    console.print(
                        f"{winner_name}'s updated stack: [bold green]{format_chips(self.game_state.players[winner_id].stack)}[/bold green]"
                    )
        console.rule(style="green")


def main() -> None:
    """Run a demonstration of Robot Hold 'Em with robot players."""
    console.clear()
    console.rule(style="bright_blue", characters="=")

    title = Text()
    title.append("\nWELCOME TO ", style="bold white")
    title.append("ROBOT HOLD 'EM POKER", style="bold red")
    title.append("\nESPN BROADCAST EDITION", style="bold cyan")
    title.append(
        "\nFEATURING LLM-POWERED PLAYERS WITH PERSONALITIES", style="bold magenta"
    )
    console.print(title, justify="center")

    console.rule(style="bright_blue", characters="=")

    # Check if OpenAI API key is available
    if not OPENAI_API_KEY:
        console.print(
            "\n[bold red]ERROR:[/bold red] OPENAI_API_KEY environment variable not set."
        )
        console.print("Please set your OpenAI API key in the .env file or environment.")
        console.print("Exiting...")
        return

    # Create the game with settings from environment variables
    game = PokerGame(
        starting_stack=STARTING_STACK,
        small_blind=SMALL_BLIND,
        big_blind=BIG_BLIND,
        broadcast_mode=BROADCAST_MODE,
        enable_commentary=True,
        commentary_frequency=0.7,
    )
    
    # Add commentators with different personalities
    game.add_commentator("commentator1", "Mike 'The Analyst' Johnson", "professional", OPENAI_MODEL)
    game.add_commentator("commentator2", "Excited Eddie", "enthusiastic", OPENAI_MODEL)
    game.add_commentator("commentator3", "Funny Fred", "comedic", OPENAI_MODEL)

    # Add LLM robot players with different personalities
    game.add_player(
        LLMPersonalities.create_robot(
            "player1", "Strategic Steve", "strategic", OPENAI_MODEL
        )
    )

    game.add_player(
        LLMPersonalities.create_robot(
            "player2", "Aggressive Andy", "aggressive", OPENAI_MODEL
        )
    )

    game.add_player(
        LLMPersonalities.create_robot(
            "player3", "Conservative Charlie", "conservative", OPENAI_MODEL
        )
    )

    game.add_player(
        LLMPersonalities.create_robot(
            "player4", "Mathematical Mike", "mathematical", OPENAI_MODEL
        )
    )

    # Add a fifth player with the unpredictable personality if desired
    game.add_player(
        LLMPersonalities.create_robot(
            "player5", "Unpredictable Ursula", "unpredictable", OPENAI_MODEL
        )
    )

    # Set up the game
    game.setup_game()

    console.print("\nTonight's players:", style="bold")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Player")
    table.add_column("Starting Stack", justify="right")

    for player_id, player in game.players.items():
        player_state = game.game_state.players[player_id]
        table.add_row(player.name, f"[green]{format_chips(player_state.stack)}[/green]")

    console.print(table)

    # Play hands based on NUM_HANDS setting
    for hand_num in range(1, NUM_HANDS + 1):
        console.print(f"\n[bold blue]HAND #{hand_num}[/bold blue]")
        game.play_hand()

    # Show final results
    console.rule(style="bright_blue", characters="=")
    console.print("\nFINAL CHIP COUNTS:", style="bold")

    # Sort players by stack size
    sorted_players = sorted(
        [(pid, p) for pid, p in game.players.items()],
        key=lambda x: game.game_state.players[x[0]].stack,
        reverse=True,
    )

    # Create a table for final results
    results_table = Table(show_header=True, header_style="bold")
    results_table.add_column("Rank", justify="center")
    results_table.add_column("Player")
    results_table.add_column("Final Stack", justify="right")

    for i, (player_id, player) in enumerate(sorted_players, 1):
        player_state = game.game_state.players[player_id]
        results_table.add_row(
            f"#{i}", player.name, f"[green]{format_chips(player_state.stack)}[/green]"
        )

    console.print(results_table)

    console.rule(style="bright_blue", characters="=")
    console.print(
        "\nThanks for watching Robot Hold 'Em Poker!",
        style="bold cyan",
        justify="center",
    )
    console.rule(style="bright_blue", characters="=")
    
    # Emit game end event
    if game.enable_commentary and game.commentator_manager and game.game_state:
        event = GameEvent(
            event_type=GameEvent.EventType.GAME_END,
            game_state=game.game_state,
            player_names=game._get_player_names_mapping()
        )
        game.commentator_manager.handle_event(event)
