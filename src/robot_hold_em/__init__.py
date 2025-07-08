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
    ) -> None:
        """Initialize the poker game.

        Args:
            starting_stack: Amount of chips each player starts with
            small_blind: Amount of the small blind
            big_blind: Amount of the big blind
            broadcast_mode: If True, shows all players' hole cards and detailed commentary
        """
        self.starting_stack = starting_stack
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.players: Dict[str, Player] = {}
        self.game_state: Optional[GameState] = None
        self.broadcast_mode = broadcast_mode

    def add_player(self, player: Player) -> None:
        """Add a player to the game.

        Args:
            player: The player to add
        """
        self.players[player.player_id] = player

    def setup_game(self) -> None:
        """Set up the game state with the current players."""
        player_ids = list(self.players.keys())
        self.game_state = GameState(
            player_ids, self.starting_stack, self.small_blind, self.big_blind
        )

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

        # Post blinds
        small_blind_pos = (self.game_state.dealer_position + 1) % len(self.players)
        big_blind_pos = (self.game_state.dealer_position + 2) % len(self.players)
        small_blind_id = list(self.players.keys())[small_blind_pos]
        big_blind_id = list(self.players.keys())[big_blind_pos]

        self._place_bet(small_blind_id, self.game_state.small_blind)
        self._place_bet(big_blind_id, self.game_state.big_blind)

        print(
            f"{self.players[small_blind_id].name} posts small blind {format_chips(self.game_state.small_blind)}"
        )
        print(
            f"{self.players[big_blind_id].name} posts big blind {format_chips(self.game_state.big_blind)}"
        )

        # Notify players of their hole cards
        print_section("HOLE CARDS")

        # Create a table for hole cards
        table = Table(box=box.SIMPLE)
        table.add_column("Player", style="bold")
        table.add_column("Hole Cards", style="bold red")
        table.add_column("Stack", style="bold green")

        for player_id, player in self.players.items():
            player_state = self.game_state.players[player_id]
            player.notify_hole_cards(player_state.hole_cards)

            # Show all robot players' cards in broadcast mode
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
            flop = self.game_state.deal_flop()
            print_section("Flop")
            console.print(
                f"Flop cards: [bold red]{flop[0]} {flop[1]} {flop[2]}[/bold red]"
            )

            # Notify players of community cards
            for player in self.players.values():
                player.notify_community_cards(self.game_state.community_cards)

            self._play_betting_round("Flop")

        # If more than one player is still in the hand, continue to the turn
        if self._count_active_players() > 1:
            turn = self.game_state.deal_turn()
            print_section("Turn")
            console.print(f"Turn card: [bold red]{turn}[/bold red]")

            # Notify players of community cards
            for player in self.players.values():
                player.notify_community_cards(self.game_state.community_cards)

            self._play_betting_round("Turn")

        # If more than one player is still in the hand, continue to the river
        if self._count_active_players() > 1:
            river = self.game_state.deal_river()
            print_section("River")
            console.print(f"River card: [bold red]{river}[/bold red]")

            # Notify players of community cards
            for player in self.players.values():
                player.notify_community_cards(self.game_state.community_cards)

            self._play_betting_round("River")

        # Show all community cards
        if self.game_state.community_cards:
            community_str = " ".join(
                str(card) for card in self.game_state.community_cards
            )
            console.print(f"\nCommunity cards: [bold red]{community_str}[/bold red]")

        # Showdown if more than one player is still in the hand
        if self._count_active_players() > 1:
            self._showdown()
        else:
            # Only one player left, they win by default
            for player_id, player_state in self.game_state.players.items():
                if not player_state.folded:
                    winner_name = self.players[player_id].name
                    print(
                        f"\n--- {winner_name} wins ${self.game_state.current_pot} by default (all others folded) ---"
                    )
                    break

    def _count_active_players(self) -> int:
        """Count the number of players still in the hand.

        Returns:
            Number of active (non-folded) players
        """
        if not self.game_state:
            return 0
        return sum(
            1
            for player_state in self.game_state.players.values()
            if not player_state.folded
        )

    def _play_betting_round(self, round_name: str) -> None:
        """Play a betting round.

        Args:
            round_name: Name of the betting round for display
        """
        if not self.game_state:
            return

        print_section(f"{round_name.upper()} BETTING")

        # Get the proper betting order (starting after the dealer/button)
        player_ids = list(self.players.keys())
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
    )

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
