"""
Deck implementation for Robot Hold 'Em poker game.
"""
import random
from typing import List, Optional

from robot_hold_em.core.card import Card, Rank, Suit


class Deck:
    """Represents a standard deck of 52 playing cards, optionally with jokers."""
    
    def __init__(self, include_jokers: bool = False) -> None:
        """Initialize a new deck with all 52 cards in order.
        
        Args:
            include_jokers: If True, include 2 jokers in the deck
        """
        self.cards: List[Card] = []
        self.include_jokers = include_jokers
        self.reset()
    
    def reset(self) -> None:
        """Reset the deck to a full set of cards in order."""
        self.cards = []
        for suit in Suit:
            if suit == Suit.JOKER:
                continue  # Skip joker suit in normal iteration
            for rank in Rank:
                if rank == Rank.JOKER:
                    continue  # Skip joker rank in normal iteration
                self.cards.append(Card(rank, suit))
        
        # Add jokers if enabled
        if self.include_jokers:
            self.cards.append(Card(Rank.JOKER, Suit.JOKER))  # Red joker
            self.cards.append(Card(Rank.JOKER, Suit.JOKER))  # Black joker
    
    def shuffle(self, seed: Optional[int] = None) -> None:
        """Shuffle the deck of cards.
        
        Args:
            seed: Optional random seed for reproducibility
        """
        if seed is not None:
            random.seed(seed)
        random.shuffle(self.cards)
    
    def deal(self) -> Card:
        """Deal a single card from the top of the deck.
        
        Returns:
            The top card from the deck
            
        Raises:
            IndexError: If the deck is empty
        """
        if not self.cards:
            raise IndexError("Cannot deal from an empty deck")
        return self.cards.pop()
    
    def deal_multiple(self, count: int) -> List[Card]:
        """Deal multiple cards from the top of the deck.
        
        Args:
            count: Number of cards to deal
            
        Returns:
            A list of cards dealt from the deck
            
        Raises:
            IndexError: If there aren't enough cards in the deck
        """
        if len(self.cards) < count:
            raise IndexError(f"Not enough cards in deck. Requested {count}, but only {len(self.cards)} available")
        
        dealt_cards = []
        for _ in range(count):
            dealt_cards.append(self.deal())
        return dealt_cards
    
    def __len__(self) -> int:
        """Return the number of cards left in the deck."""
        return len(self.cards)
    
    def __str__(self) -> str:
        """Return a string representation of the deck."""
        deck_size = 54 if self.include_jokers else 52
        return f"Deck with {len(self.cards)} cards remaining (out of {deck_size})"
