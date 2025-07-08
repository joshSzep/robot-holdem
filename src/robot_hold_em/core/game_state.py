"""
Game state management for Robot Hold 'Em poker game.
"""
from enum import Enum, auto
from typing import Dict, List, Optional

from robot_hold_em.core.card import Card
from robot_hold_em.core.deck import Deck


class BettingRound(Enum):
    """Represents the different betting rounds in Texas Hold 'Em."""
    PREFLOP = auto()
    FLOP = auto()
    TURN = auto()
    RIVER = auto()
    SHOWDOWN = auto()
    
    def __str__(self) -> str:
        """Return a human-readable string representation of the betting round."""
        return self.name.capitalize()
    
    def next_round(self) -> 'BettingRound':
        """Return the next betting round."""
        rounds = list(BettingRound)
        current_index = rounds.index(self)
        if current_index < len(rounds) - 1:
            return rounds[current_index + 1]
        return self  # Return the current round if it's the last one


class PlayerAction(Enum):
    """Represents the possible actions a player can take during their turn."""
    FOLD = auto()
    CHECK = auto()
    CALL = auto()
    BET = auto()
    RAISE = auto()
    ALL_IN = auto()
    
    def __str__(self) -> str:
        """Return a human-readable string representation of the player action."""
        return self.name.capitalize()


class PlayerState:
    """Represents the state of a player in the game."""
    
    def __init__(self, player_id: str, stack: int) -> None:
        """Initialize a player state.
        
        Args:
            player_id: Unique identifier for the player
            stack: Amount of chips the player starts with
        """
        self.player_id = player_id
        self.stack = stack
        self.hole_cards: List[Card] = []
        self.current_bet = 0
        self.folded = False
        self.all_in = False
        self.last_action: Optional[PlayerAction] = None
    
    def reset_for_new_hand(self) -> None:
        """Reset the player state for a new hand."""
        self.hole_cards = []
        self.current_bet = 0
        self.folded = False
        self.all_in = False
        self.last_action = None
    
    def __str__(self) -> str:
        """Return a string representation of the player state."""
        status = "folded" if self.folded else "active"
        if self.all_in:
            status = "all-in"
        
        cards_str = ", ".join(str(card) for card in self.hole_cards) if self.hole_cards else "hidden"
        
        return f"Player {self.player_id}: {status}, stack: {self.stack}, bet: {self.current_bet}, cards: {cards_str}"


class GameState:
    """Manages the state of a Texas Hold 'Em poker game."""
    
    def __init__(self, player_ids: List[str], starting_stack: int, small_blind: int, big_blind: int) -> None:
        """Initialize the game state.
        
        Args:
            player_ids: List of player identifiers
            starting_stack: Amount of chips each player starts with
            small_blind: Amount of the small blind
            big_blind: Amount of the big blind
        """
        self.players = {player_id: PlayerState(player_id, starting_stack) for player_id in player_ids}
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.deck = Deck()
        self.community_cards: List[Card] = []
        self.pots: List[Dict] = []  # List of pots (main pot and side pots)
        self.current_pot = 0  # Total amount in the current pot
        self.betting_round = BettingRound.PREFLOP
        self.dealer_position = 0
        self.current_player_index = 0
        self.last_aggressor_index = 0
        self.min_raise = big_blind
    
    def reset_for_new_hand(self) -> None:
        """Reset the game state for a new hand."""
        # Reset deck and shuffle
        self.deck.reset()
        self.deck.shuffle()
        
        # Reset community cards and pot
        self.community_cards = []
        self.pots = []
        self.current_pot = 0
        
        # Reset betting round and positions
        self.betting_round = BettingRound.PREFLOP
        self.dealer_position = (self.dealer_position + 1) % len(self.players)
        self.current_player_index = (self.dealer_position + 3) % len(self.players)  # Start with player after big blind
        self.last_aggressor_index = self.current_player_index
        self.min_raise = self.big_blind
        
        # Reset player states
        for player in self.players.values():
            player.reset_for_new_hand()
        
        # Post blinds
        self._post_blinds()
        
        # Deal hole cards
        self._deal_hole_cards()
    
    def _post_blinds(self) -> None:
        """Post the small and big blinds."""
        small_blind_pos = (self.dealer_position + 1) % len(self.players)
        big_blind_pos = (self.dealer_position + 2) % len(self.players)
        
        small_blind_player_id = list(self.players.keys())[small_blind_pos]
        big_blind_player_id = list(self.players.keys())[big_blind_pos]
        
        # Post small blind
        self._place_bet(small_blind_player_id, self.small_blind)
        self.players[small_blind_player_id].last_action = PlayerAction.BET
        
        # Post big blind
        self._place_bet(big_blind_player_id, self.big_blind)
        self.players[big_blind_player_id].last_action = PlayerAction.BET
    
    def _deal_hole_cards(self) -> None:
        """Deal two hole cards to each player."""
        for player in self.players.values():
            player.hole_cards = self.deck.deal_multiple(2)
    
    def deal_flop(self) -> List[Card]:
        """Deal the flop (first three community cards).
        
        Returns:
            The three flop cards
        """
        # Burn a card
        self.deck.deal()
        
        # Deal the flop
        flop_cards = self.deck.deal_multiple(3)
        self.community_cards.extend(flop_cards)
        self.betting_round = BettingRound.FLOP
        
        return flop_cards
    
    def deal_turn(self) -> Card:
        """Deal the turn (fourth community card).
        
        Returns:
            The turn card
        """
        # Burn a card
        self.deck.deal()
        
        # Deal the turn
        turn_card = self.deck.deal()
        self.community_cards.append(turn_card)
        self.betting_round = BettingRound.TURN
        
        return turn_card
    
    def deal_river(self) -> Card:
        """Deal the river (fifth community card).
        
        Returns:
            The river card
        """
        # Burn a card
        self.deck.deal()
        
        # Deal the river
        river_card = self.deck.deal()
        self.community_cards.append(river_card)
        self.betting_round = BettingRound.RIVER
        
        return river_card
    
    def _place_bet(self, player_id: str, amount: int) -> None:
        """Place a bet for a player.
        
        Args:
            player_id: ID of the player placing the bet
            amount: Amount to bet
        """
        player = self.players[player_id]
        
        # Cap the bet at the player's stack (all-in)
        actual_amount = min(amount, player.stack)
        
        player.stack -= actual_amount
        player.current_bet += actual_amount
        self.current_pot += actual_amount
        
        # Check if player is all-in
        if player.stack == 0:
            player.all_in = True
    
    def get_current_player(self) -> PlayerState:
        """Get the current player whose turn it is.
        
        Returns:
            The current player state
        """
        player_id = list(self.players.keys())[self.current_player_index]
        return self.players[player_id]
    
    def next_player(self) -> PlayerState:
        """Move to the next player in the hand.
        
        Returns:
            The next player state
        """
        # Find the next active player
        player_ids = list(self.players.keys())
        original_index = self.current_player_index
        
        while True:
            self.current_player_index = (self.current_player_index + 1) % len(player_ids)
            player = self.players[player_ids[self.current_player_index]]
            
            # Skip folded players
            if not player.folded:
                break
                
            # If we've gone all the way around, return to the original player
            if self.current_player_index == original_index:
                break
        
        return self.get_current_player()
    
    def is_betting_round_complete(self) -> bool:
        """Check if the current betting round is complete.
        
        Returns:
            True if the betting round is complete, False otherwise
        """
        # Count active (non-folded) players
        active_players = [p for p in self.players.values() if not p.folded]
        
        # If only one player is left, the round is complete
        if len(active_players) == 1:
            return True
        
        # If all active players have acted and bets are equal or players are all-in
        current_bet = max(p.current_bet for p in active_players)
        for player in active_players:
            if player.current_bet < current_bet and not player.all_in:
                return False
            if player.last_action is None:
                return False
        
        return True
    
    def move_to_next_betting_round(self) -> None:
        """Move to the next betting round."""
        # Reset player bets for the new round
        for player in self.players.values():
            player.current_bet = 0
            player.last_action = None
        
        # Reset the minimum raise
        self.min_raise = self.big_blind
        
        # Move to the next round
        self.betting_round = self.betting_round.next_round()
        
        # Set the first active player after the dealer to act first
        self.current_player_index = self.dealer_position
        self.next_player()  # Move to the first active player
    
    def get_player_hand(self, player_id: str) -> List[Card]:
        """Get the complete hand for a player (hole cards + community cards).
        
        Args:
            player_id: ID of the player
            
        Returns:
            List of cards forming the player's hand
        """
        return self.players[player_id].hole_cards + self.community_cards
    
    def get_player_by_id(self, player_id: str) -> 'PlayerState':
        """Get a player state by their ID.
        
        Args:
            player_id: ID of the player
            
        Returns:
            The player state for the given ID
        """
        return self.players[player_id]
    
    def __str__(self) -> str:
        """Return a string representation of the game state."""
        result = [f"Betting Round: {self.betting_round}"]
        result.append(f"Pot: {self.current_pot}")
        
        if self.community_cards:
            cards_str = " ".join(str(card) for card in self.community_cards)
            result.append(f"Community Cards: {cards_str}")
        else:
            result.append("Community Cards: None")
        
        result.append("Players:")
        for player in self.players.values():
            result.append(f"  {player}")
        
        return "\n".join(result)
