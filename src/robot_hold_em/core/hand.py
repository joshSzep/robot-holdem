"""
Hand evaluation logic for Robot Hold 'Em poker game.
"""
from collections import Counter
from enum import Enum, auto
from itertools import combinations
from typing import Dict, List, Optional, Tuple

from robot_hold_em.core.card import Card, Rank, Suit


class HandRank(Enum):
    """Represents the possible poker hand rankings in ascending order of value."""
    HIGH_CARD = auto()
    ONE_PAIR = auto()
    TWO_PAIR = auto()
    THREE_OF_A_KIND = auto()
    STRAIGHT = auto()
    FLUSH = auto()
    FULL_HOUSE = auto()
    FOUR_OF_A_KIND = auto()
    STRAIGHT_FLUSH = auto()
    ROYAL_FLUSH = auto()
    
    def __str__(self) -> str:
        """Return a human-readable string representation of the hand rank."""
        return self.name.replace("_", " ").title()


class Hand:
    """Represents a poker hand and provides methods for evaluation."""
    
    def __init__(self, cards: List[Card]) -> None:
        """Initialize a hand with a list of cards.
        
        Args:
            cards: List of cards in the hand
        """
        self.cards = sorted(cards, reverse=True)  # Sort by rank, highest first
    
    def __str__(self) -> str:
        """Return a string representation of the hand."""
        return " ".join(str(card) for card in self.cards)
    
    @property
    def ranks(self) -> List[Rank]:
        """Return a list of card ranks in the hand."""
        return [card.rank for card in self.cards]
    
    @property
    def suits(self) -> List[Suit]:
        """Return a list of card suits in the hand."""
        return [card.suit for card in self.cards]
    
    def rank_counts(self) -> Dict[Rank, int]:
        """Count occurrences of each rank in the hand."""
        return Counter(self.ranks)
    
    def suit_counts(self) -> Dict[Suit, int]:
        """Count occurrences of each suit in the hand."""
        return Counter(self.suits)


class HandEvaluator:
    """Evaluates poker hands to determine their ranking."""
    
    @staticmethod
    def evaluate(cards: List[Card]) -> Tuple[HandRank, List[Card]]:
        """Evaluate a set of cards to determine the best poker hand.
        
        In Texas Hold'em, players make their best 5-card hand from 7 cards
        (2 hole cards + 5 community cards).
        
        Args:
            cards: List of cards to evaluate (typically 7 cards in Texas Hold'em)
            
        Returns:
            A tuple containing the hand rank and the 5 cards that make up the best hand
        """
        # Check if there are any jokers (wild cards)
        has_jokers = any(card.is_joker() for card in cards)
        
        if has_jokers:
            return HandEvaluator._evaluate_with_wildcards(cards)
        
        # We need to find the best 5-card hand from the given cards
        hand = Hand(cards)
        
        # Check for each hand rank in descending order of value
        royal_flush = HandEvaluator._find_royal_flush(hand)
        if royal_flush:
            return HandRank.ROYAL_FLUSH, royal_flush
            
        straight_flush = HandEvaluator._find_straight_flush(hand)
        if straight_flush:
            return HandRank.STRAIGHT_FLUSH, straight_flush
            
        four_of_a_kind = HandEvaluator._find_four_of_a_kind(hand)
        if four_of_a_kind:
            return HandRank.FOUR_OF_A_KIND, four_of_a_kind
            
        full_house = HandEvaluator._find_full_house(hand)
        if full_house:
            return HandRank.FULL_HOUSE, full_house
            
        flush = HandEvaluator._find_flush(hand)
        if flush:
            return HandRank.FLUSH, flush
            
        straight = HandEvaluator._find_straight(hand)
        if straight:
            return HandRank.STRAIGHT, straight
            
        three_of_a_kind = HandEvaluator._find_three_of_a_kind(hand)
        if three_of_a_kind:
            return HandRank.THREE_OF_A_KIND, three_of_a_kind
            
        two_pair = HandEvaluator._find_two_pair(hand)
        if two_pair:
            return HandRank.TWO_PAIR, two_pair
            
        one_pair = HandEvaluator._find_one_pair(hand)
        if one_pair:
            return HandRank.ONE_PAIR, one_pair
            
        # If no other hand pattern is found, return the highest 5 cards
        return HandRank.HIGH_CARD, hand.cards[:5]
    
    @staticmethod 
    def _evaluate_with_wildcards(cards: List[Card]) -> Tuple[HandRank, List[Card]]:
        """Evaluate the best possible hand considering jokers as wild cards.
        
        Args:
            cards: List of cards including potential jokers
            
        Returns:
            A tuple containing the best hand rank and the 5 cards that make up the best hand
        """
        jokers = [card for card in cards if card.is_joker()]
        non_jokers = [card for card in cards if not card.is_joker()]
        
        if len(jokers) >= 4:
            # With 4+ jokers, we can always make at least a four of a kind
            # with more jokers, we can make a royal flush
            if len(jokers) >= 5 or (len(jokers) == 4 and len(non_jokers) >= 1):
                # Create royal flush
                royal_flush = [
                    Card(Rank.ACE, Suit.SPADES),
                    Card(Rank.KING, Suit.SPADES),
                    Card(Rank.QUEEN, Suit.SPADES),
                    Card(Rank.JACK, Suit.SPADES),
                    Card(Rank.TEN, Suit.SPADES)
                ]
                return HandRank.ROYAL_FLUSH, royal_flush
        
        # For simpler wild card handling, we'll use a basic approach:
        # Try some common high-value hand patterns with jokers
        
        num_jokers = len(jokers)
        
        if num_jokers >= 1:
            # With at least 1 joker, we can improve any hand significantly
            # For simplicity, let's assume jokers always improve to the best possible hand
            # given the remaining cards
            
            # If we have a pair in non-jokers, jokers can make it four of a kind or better
            ranks = [card.rank for card in non_jokers]
            rank_counts = Counter(ranks)
            
            # Check for pairs that can be improved
            for rank, count in rank_counts.items():
                if count >= 2 and num_jokers >= 2:
                    # Can make four of a kind
                    four_cards = [card for card in non_jokers if card.rank == rank][:2]
                    # Add two jokers as the same rank
                    four_cards.extend([Card(rank, Suit.SPADES), Card(rank, Suit.HEARTS)])
                    # Add highest kicker
                    kickers = [card for card in non_jokers if card.rank != rank]
                    kickers.sort(reverse=True)
                    if kickers:
                        four_cards.append(kickers[0])
                    else:
                        four_cards.append(Card(Rank.ACE, Suit.CLUBS))
                    return HandRank.FOUR_OF_A_KIND, four_cards[:5]
            
            # If we have high cards, make them into a straight or flush
            if num_jokers >= 1:
                # Try to make the highest possible hand with available cards
                # For simplicity, create a straight with high cards
                non_jokers_sorted = sorted(non_jokers, reverse=True)
                best_hand = non_jokers_sorted[:5-num_jokers]
                
                # Fill remaining spots with high cards
                high_ranks = [Rank.ACE, Rank.KING, Rank.QUEEN, Rank.JACK, Rank.TEN]
                used_ranks = {card.rank for card in best_hand}
                
                for rank in high_ranks:
                    if len(best_hand) < 5 and rank not in used_ranks:
                        best_hand.append(Card(rank, Suit.SPADES))
                
                # If we still need cards, add them
                while len(best_hand) < 5:
                    best_hand.append(Card(Rank.ACE, Suit.HEARTS))
                
                # Determine the best hand type we can make
                if num_jokers >= 3:
                    return HandRank.FOUR_OF_A_KIND, best_hand
                elif num_jokers >= 2:
                    return HandRank.THREE_OF_A_KIND, best_hand
                else:
                    return HandRank.ONE_PAIR, best_hand
        
        # Fallback to normal evaluation if no jokers
        return HandEvaluator.evaluate(non_jokers)
    
    @staticmethod
    def _find_royal_flush(hand: Hand) -> Optional[List[Card]]:
        """Find a royal flush in the hand."""
        # A royal flush is a straight flush with Ace high
        straight_flush = HandEvaluator._find_straight_flush(hand)
        if straight_flush and straight_flush[0].rank == Rank.ACE:
            return straight_flush
        return None
    
    @staticmethod
    def _find_straight_flush(hand: Hand) -> Optional[List[Card]]:
        """Find a straight flush in the hand."""
        # Group cards by suit
        suit_groups = {}
        for card in hand.cards:
            if card.suit not in suit_groups:
                suit_groups[card.suit] = []
            suit_groups[card.suit].append(card)
        
        # Check each suit group for a straight
        for suit, cards in suit_groups.items():
            if len(cards) >= 5:
                temp_hand = Hand(cards)
                straight = HandEvaluator._find_straight(temp_hand)
                if straight:
                    return straight
        
        return None
    
    @staticmethod
    def _find_four_of_a_kind(hand: Hand) -> Optional[List[Card]]:
        """Find four of a kind in the hand."""
        rank_counts = hand.rank_counts()
        
        for rank, count in rank_counts.items():
            if count == 4:
                # Get the four cards of the same rank
                four_cards = [card for card in hand.cards if card.rank == rank]
                
                # Add the highest remaining card as a kicker
                kickers = [card for card in hand.cards if card.rank != rank]
                result = four_cards + kickers[:1]
                
                return result
        
        return None
    
    @staticmethod
    def _find_full_house(hand: Hand) -> Optional[List[Card]]:
        """Find a full house in the hand."""
        rank_counts = hand.rank_counts()
        
        # Find the highest three of a kind
        three_of_a_kind_rank = None
        for rank, count in rank_counts.items():
            if count >= 3:
                if three_of_a_kind_rank is None or rank.value > three_of_a_kind_rank.value:
                    three_of_a_kind_rank = rank
        
        if three_of_a_kind_rank is None:
            return None
        
        # Find the highest pair that's different from the three of a kind
        pair_rank = None
        for rank, count in rank_counts.items():
            if count >= 2 and rank != three_of_a_kind_rank:
                if pair_rank is None or rank.value > pair_rank.value:
                    pair_rank = rank
        
        if pair_rank is None:
            return None
        
        # Get the three cards of the three of a kind
        three_cards = [card for card in hand.cards if card.rank == three_of_a_kind_rank][:3]
        
        # Get the two cards of the pair
        pair_cards = [card for card in hand.cards if card.rank == pair_rank][:2]
        
        return three_cards + pair_cards
    
    @staticmethod
    def _find_flush(hand: Hand) -> Optional[List[Card]]:
        """Find a flush in the hand."""
        suit_counts = hand.suit_counts()
        
        for suit, count in suit_counts.items():
            if count >= 5:
                flush_cards = [card for card in hand.cards if card.suit == suit]
                return flush_cards[:5]  # Return the 5 highest cards of the flush
        
        return None
    
    @staticmethod
    def _find_straight(hand: Hand) -> Optional[List[Card]]:
        """Find a straight in the hand."""
        # Remove duplicate ranks
        unique_ranks = []
        seen_ranks = set()
        for card in hand.cards:
            if card.rank not in seen_ranks:
                unique_ranks.append(card)
                seen_ranks.add(card.rank)
        
        # Check for A-5-4-3-2 straight (Ace low)
        if (Rank.ACE in seen_ranks and Rank.FIVE in seen_ranks and
                Rank.FOUR in seen_ranks and Rank.THREE in seen_ranks and
                Rank.TWO in seen_ranks):
            # Find the cards with these ranks
            ace = next(card for card in hand.cards if card.rank == Rank.ACE)
            five = next(card for card in hand.cards if card.rank == Rank.FIVE)
            four = next(card for card in hand.cards if card.rank == Rank.FOUR)
            three = next(card for card in hand.cards if card.rank == Rank.THREE)
            two = next(card for card in hand.cards if card.rank == Rank.TWO)
            return [five, four, three, two, ace]  # Ace is low in this case
        
        # Check for regular straights
        for i in range(len(unique_ranks) - 4):
            if (unique_ranks[i].rank.value == unique_ranks[i+1].rank.value + 1 and
                    unique_ranks[i+1].rank.value == unique_ranks[i+2].rank.value + 1 and
                    unique_ranks[i+2].rank.value == unique_ranks[i+3].rank.value + 1 and
                    unique_ranks[i+3].rank.value == unique_ranks[i+4].rank.value + 1):
                return unique_ranks[i:i+5]
        
        return None
    
    @staticmethod
    def _find_three_of_a_kind(hand: Hand) -> Optional[List[Card]]:
        """Find three of a kind in the hand."""
        rank_counts = hand.rank_counts()
        
        for rank, count in rank_counts.items():
            if count == 3:
                # Get the three cards of the same rank
                three_cards = [card for card in hand.cards if card.rank == rank]
                
                # Add the two highest remaining cards as kickers
                kickers = [card for card in hand.cards if card.rank != rank]
                result = three_cards + kickers[:2]
                
                return result
        
        return None
    
    @staticmethod
    def _find_two_pair(hand: Hand) -> Optional[List[Card]]:
        """Find two pair in the hand."""
        rank_counts = hand.rank_counts()
        
        pairs = []
        for rank, count in rank_counts.items():
            if count >= 2:
                pairs.append(rank)
        
        if len(pairs) >= 2:
            # Sort pairs by rank value (highest first)
            pairs.sort(key=lambda r: r.value, reverse=True)
            
            # Get the two highest pairs
            first_pair = [card for card in hand.cards if card.rank == pairs[0]][:2]
            second_pair = [card for card in hand.cards if card.rank == pairs[1]][:2]
            
            # Add the highest remaining card as a kicker
            kickers = [card for card in hand.cards 
                      if card.rank != pairs[0] and card.rank != pairs[1]]
            
            result = first_pair + second_pair + kickers[:1]
            
            return result
        
        return None
    
    @staticmethod
    def _find_one_pair(hand: Hand) -> Optional[List[Card]]:
        """Find one pair in the hand."""
        rank_counts = hand.rank_counts()
        
        for rank, count in rank_counts.items():
            if count >= 2:
                # Get the two cards of the same rank
                pair_cards = [card for card in hand.cards if card.rank == rank][:2]
                
                # Add the three highest remaining cards as kickers
                kickers = [card for card in hand.cards if card.rank != rank]
                result = pair_cards + kickers[:3]
                
                return result
        
        return None


class HandComparator:
    """Compares poker hands to determine the winner."""
    
    @staticmethod
    def compare_hands(hand1: List[Card], hand2: List[Card]) -> int:
        """Compare two poker hands to determine which is stronger.
        
        Args:
            hand1: First hand to compare
            hand2: Second hand to compare
            
        Returns:
            1 if hand1 is stronger, -1 if hand2 is stronger, 0 if they are equal
        """
        rank1, best_hand1 = HandEvaluator.evaluate(hand1)
        rank2, best_hand2 = HandEvaluator.evaluate(hand2)
        
        # Compare hand ranks first
        if rank1.value > rank2.value:
            return 1
        elif rank1.value < rank2.value:
            return -1
        
        # If hand ranks are equal, compare the cards in each hand
        for card1, card2 in zip(best_hand1, best_hand2):
            if card1.rank.value > card2.rank.value:
                return 1
            elif card1.rank.value < card2.rank.value:
                return -1
        
        # If all cards are equal, it's a tie
        return 0
