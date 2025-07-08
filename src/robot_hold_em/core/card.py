"""
Card representation for Robot Hold 'Em poker game.
"""
from enum import Enum, auto
from typing import Self


class Suit(Enum):
    """Represents the four suits in a standard deck of cards."""
    CLUBS = auto()
    DIAMONDS = auto()
    HEARTS = auto()
    SPADES = auto()
    
    def __str__(self) -> str:
        """Return a string representation of the suit."""
        return self.name.capitalize()
    
    @property
    def symbol(self) -> str:
        """Return the symbol for the suit."""
        symbols = {
            Suit.CLUBS: "♣",
            Suit.DIAMONDS: "♦",
            Suit.HEARTS: "♥",
            Suit.SPADES: "♠",
        }
        return symbols[self]


class Rank(Enum):
    """Represents the thirteen ranks in a standard deck of cards."""
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14
    
    def __str__(self) -> str:
        """Return a string representation of the rank."""
        names = {
            Rank.TWO: "2",
            Rank.THREE: "3",
            Rank.FOUR: "4",
            Rank.FIVE: "5",
            Rank.SIX: "6",
            Rank.SEVEN: "7",
            Rank.EIGHT: "8",
            Rank.NINE: "9",
            Rank.TEN: "10",
            Rank.JACK: "J",
            Rank.QUEEN: "Q",
            Rank.KING: "K",
            Rank.ACE: "A",
        }
        return names[self]


class Card:
    """Represents a playing card with a suit and rank."""
    
    def __init__(self, rank: Rank, suit: Suit) -> None:
        """Initialize a card with a rank and suit.
        
        Args:
            rank: The rank of the card
            suit: The suit of the card
        """
        self.rank = rank
        self.suit = suit
    
    def __str__(self) -> str:
        """Return a string representation of the card."""
        return f"{self.rank}{self.suit.symbol}"
    
    def __repr__(self) -> str:
        """Return a string representation of the card for debugging."""
        return f"Card({self.rank}, {self.suit})"
    
    def __eq__(self, other: Self) -> bool:
        """Check if two cards are equal."""
        if not isinstance(other, Card):
            return NotImplemented
        return self.rank == other.rank and self.suit == other.suit
    
    def __lt__(self, other: Self) -> bool:
        """Compare cards by rank."""
        if not isinstance(other, Card):
            return NotImplemented
        return self.rank.value < other.rank.value
