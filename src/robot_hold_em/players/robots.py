"""
Robot player implementations with different strategies for Robot Hold 'Em.
"""
import random
from typing import Dict, Optional, Tuple

from robot_hold_em.core import GameState, HandEvaluator, HandRank, PlayerAction
from robot_hold_em.players.base import RobotPlayer


class RandomRobot(RobotPlayer):
    """A robot player that makes completely random decisions."""
    
    def get_action(self, game_state: GameState) -> Tuple[PlayerAction, Optional[int]]:
        """Choose a random action.
        
        Args:
            game_state: Current state of the game
            
        Returns:
            A tuple containing the action and the bet amount (if applicable)
        """
        # Get the current player state
        player_state = game_state.players[self.player_id]
        
        # Get the current highest bet
        current_highest_bet = max(p.current_bet for p in game_state.players.values())
        
        # Calculate how much more we need to call
        call_amount = current_highest_bet - player_state.current_bet
        
        # Available actions depend on the situation
        available_actions = []
        
        # Can always fold
        available_actions.append(PlayerAction.FOLD)
        
        # Can check if no one has bet or we've already matched the highest bet
        if call_amount == 0:
            available_actions.append(PlayerAction.CHECK)
        
        # Can call if someone has bet and we have enough chips
        if call_amount > 0 and player_state.stack >= call_amount:
            available_actions.append(PlayerAction.CALL)
        
        # Can bet or raise if we have chips left after calling
        if player_state.stack > call_amount:
            if call_amount == 0:
                available_actions.append(PlayerAction.BET)
            else:
                available_actions.append(PlayerAction.RAISE)
        
        # Choose a random action
        action = random.choice(available_actions)
        
        # Determine bet amount if needed
        bet_amount = None
        if action == PlayerAction.BET:
            # Random bet between min_bet and stack
            min_bet = game_state.big_blind
            max_bet = player_state.stack
            bet_amount = random.randint(min_bet, max(min_bet, max_bet))
        elif action == PlayerAction.RAISE:
            # Random raise between min_raise and stack
            min_raise = call_amount + game_state.min_raise
            max_raise = player_state.stack
            bet_amount = random.randint(min_raise, max(min_raise, max_raise))
        elif action == PlayerAction.CALL:
            bet_amount = call_amount
        
        return action, bet_amount


class ConservativeRobot(RobotPlayer):
    """A conservative robot player that only plays strong hands."""
    
    def _evaluate_hand_strength(self) -> float:
        """Evaluate the strength of the current hand on a scale of 0 to 1.
        
        Returns:
            A float representing hand strength (0 = weakest, 1 = strongest)
        """
        # If we don't have hole cards yet, return minimum strength
        if not self.hole_cards:
            return 0.0
        
        # Preflop evaluation based on hole cards only
        if not self.community_cards:
            # Check for pocket pairs
            if self.hole_cards[0].rank == self.hole_cards[1].rank:
                # Rank the pair from 0.5 (lowest pair) to 0.9 (highest pair)
                return 0.5 + 0.4 * (self.hole_cards[0].rank.value - 2) / 12
            
            # Check for suited cards
            suited = self.hole_cards[0].suit == self.hole_cards[1].suit
            
            # Calculate the strength based on ranks
            high_card = max(self.hole_cards[0].rank.value, self.hole_cards[1].rank.value)
            low_card = min(self.hole_cards[0].rank.value, self.hole_cards[1].rank.value)
            
            # Connected cards (consecutive ranks) are stronger
            connected = high_card - low_card == 1
            
            # Base strength on high card
            strength = 0.1 + 0.3 * (high_card - 2) / 12
            
            # Bonus for suited and connected
            if suited:
                strength += 0.1
            if connected:
                strength += 0.1
            
            return min(strength, 0.5)  # Cap non-pair hands at 0.5 preflop
        
        # Postflop evaluation based on all available cards
        all_cards = self.hole_cards + self.community_cards
        rank, _ = HandEvaluator.evaluate(all_cards)
        
        # Map hand ranks to strength values
        hand_rank_strength: Dict[HandRank, float] = {
            HandRank.HIGH_CARD: 0.1,
            HandRank.ONE_PAIR: 0.2,
            HandRank.TWO_PAIR: 0.4,
            HandRank.THREE_OF_A_KIND: 0.6,
            HandRank.STRAIGHT: 0.7,
            HandRank.FLUSH: 0.8,
            HandRank.FULL_HOUSE: 0.9,
            HandRank.FOUR_OF_A_KIND: 0.95,
            HandRank.STRAIGHT_FLUSH: 0.98,
            HandRank.ROYAL_FLUSH: 1.0
        }
        
        return hand_rank_strength[rank]
    
    def get_action(self, game_state: GameState) -> Tuple[PlayerAction, Optional[int]]:
        """Choose an action based on a conservative strategy.
        
        Args:
            game_state: Current state of the game
            
        Returns:
            A tuple containing the action and the bet amount (if applicable)
        """
        # Get the current player state
        player_state = game_state.players[self.player_id]
        
        # Get the current highest bet
        current_highest_bet = max(p.current_bet for p in game_state.players.values())
        
        # Calculate how much more we need to call
        call_amount = current_highest_bet - player_state.current_bet
        
        # Evaluate hand strength
        hand_strength = self._evaluate_hand_strength()
        
        # Conservative strategy: only play strong hands
        if hand_strength < 0.3:
            # Weak hand: check if possible, otherwise fold
            if call_amount == 0:
                return PlayerAction.CHECK, None
            else:
                return PlayerAction.FOLD, None
        elif hand_strength < 0.6:
            # Medium hand: call small bets, fold to big bets
            if call_amount == 0:
                return PlayerAction.CHECK, None
            elif call_amount <= game_state.big_blind * 2:
                return PlayerAction.CALL, call_amount
            else:
                return PlayerAction.FOLD, None
        else:
            # Strong hand: call or raise
            if call_amount == 0:
                # No one has bet, make a bet
                bet_amount = game_state.big_blind * 2
                return PlayerAction.BET, min(bet_amount, player_state.stack)
            else:
                # Someone has bet, raise if very strong hand
                if hand_strength > 0.8 and player_state.stack > call_amount * 2:
                    raise_amount = min(call_amount * 2, player_state.stack)
                    return PlayerAction.RAISE, raise_amount
                else:
                    # Just call
                    return PlayerAction.CALL, call_amount


class AggressiveRobot(RobotPlayer):
    """An aggressive robot player that frequently bets and raises."""
    
    def _evaluate_hand_strength(self) -> float:
        """Evaluate the strength of the current hand on a scale of 0 to 1.
        
        Returns:
            A float representing hand strength (0 = weakest, 1 = strongest)
        """
        # Similar to ConservativeRobot but with more optimistic evaluation
        # If we don't have hole cards yet, return minimum strength
        if not self.hole_cards:
            return 0.0
        
        # Preflop evaluation based on hole cards only
        if not self.community_cards:
            # Check for pocket pairs
            if self.hole_cards[0].rank == self.hole_cards[1].rank:
                # Rank the pair from 0.6 (lowest pair) to 0.95 (highest pair)
                return 0.6 + 0.35 * (self.hole_cards[0].rank.value - 2) / 12
            
            # Check for suited cards
            suited = self.hole_cards[0].suit == self.hole_cards[1].suit
            
            # Calculate the strength based on ranks
            high_card = max(self.hole_cards[0].rank.value, self.hole_cards[1].rank.value)
            low_card = min(self.hole_cards[0].rank.value, self.hole_cards[1].rank.value)
            
            # Connected cards (consecutive ranks) are stronger
            connected = high_card - low_card == 1
            
            # Base strength on high card
            strength = 0.2 + 0.4 * (high_card - 2) / 12
            
            # Bonus for suited and connected
            if suited:
                strength += 0.15
            if connected:
                strength += 0.15
            
            return min(strength, 0.6)  # Cap non-pair hands at 0.6 preflop
        
        # Postflop evaluation based on all available cards
        all_cards = self.hole_cards + self.community_cards
        rank, _ = HandEvaluator.evaluate(all_cards)
        
        # Map hand ranks to strength values (more optimistic than conservative)
        hand_rank_strength: Dict[HandRank, float] = {
            HandRank.HIGH_CARD: 0.2,
            HandRank.ONE_PAIR: 0.4,
            HandRank.TWO_PAIR: 0.6,
            HandRank.THREE_OF_A_KIND: 0.7,
            HandRank.STRAIGHT: 0.8,
            HandRank.FLUSH: 0.85,
            HandRank.FULL_HOUSE: 0.9,
            HandRank.FOUR_OF_A_KIND: 0.95,
            HandRank.STRAIGHT_FLUSH: 0.98,
            HandRank.ROYAL_FLUSH: 1.0
        }
        
        return hand_rank_strength[rank]
    
    def get_action(self, game_state: GameState) -> Tuple[PlayerAction, Optional[int]]:
        """Choose an action based on an aggressive strategy.
        
        Args:
            game_state: Current state of the game
            
        Returns:
            A tuple containing the action and the bet amount (if applicable)
        """
        # Get the current player state
        player_state = game_state.players[self.player_id]
        
        # Get the current highest bet
        current_highest_bet = max(p.current_bet for p in game_state.players.values())
        
        # Calculate how much more we need to call
        call_amount = current_highest_bet - player_state.current_bet
        
        # Evaluate hand strength
        hand_strength = self._evaluate_hand_strength()
        
        # Add some randomness to be unpredictable
        bluff_factor = random.random() * 0.3  # 0 to 0.3 bluff boost
        effective_strength = min(1.0, hand_strength + bluff_factor)
        
        # Aggressive strategy: bet and raise frequently
        if effective_strength < 0.2:
            # Very weak hand: check if possible, otherwise fold
            if call_amount == 0:
                return PlayerAction.CHECK, None
            else:
                # Occasionally bluff with a very weak hand
                if random.random() < 0.1:
                    bet_amount = game_state.big_blind * 2
                    return PlayerAction.RAISE, min(bet_amount, player_state.stack)
                else:
                    return PlayerAction.FOLD, None
        elif effective_strength < 0.4:
            # Weak hand: check if possible, call small bets, occasionally bluff
            if call_amount == 0:
                # Occasionally bet with a weak hand
                if random.random() < 0.3:
                    bet_amount = game_state.big_blind * 2
                    return PlayerAction.BET, min(bet_amount, player_state.stack)
                else:
                    return PlayerAction.CHECK, None
            elif call_amount <= game_state.big_blind * 3:
                return PlayerAction.CALL, call_amount
            else:
                return PlayerAction.FOLD, None
        else:
            # Medium to strong hand: bet or raise aggressively
            if call_amount == 0:
                # No one has bet, make a bet
                bet_amount = int(game_state.big_blind * (2 + effective_strength * 4))
                return PlayerAction.BET, min(bet_amount, player_state.stack)
            else:
                # Someone has bet, raise aggressively
                if effective_strength > 0.5 and player_state.stack > call_amount * 2:
                    raise_factor = 2 + int(effective_strength * 3)  # 2-5x raise
                    raise_amount = min(call_amount * raise_factor, player_state.stack)
                    return PlayerAction.RAISE, raise_amount
                else:
                    # Just call
                    return PlayerAction.CALL, call_amount


class TightAggressiveRobot(RobotPlayer):
    """A tight-aggressive (TAG) robot player that plays few hands but plays them strongly."""
    
    def _evaluate_hand_strength(self) -> float:
        """Evaluate the strength of the current hand on a scale of 0 to 1.
        
        Returns:
            A float representing hand strength (0 = weakest, 1 = strongest)
        """
        # If we don't have hole cards yet, return minimum strength
        if not self.hole_cards:
            return 0.0
        
        # Preflop evaluation based on hole cards only
        if not self.community_cards:
            # Premium starting hands
            premium_hands = [
                # Pocket pairs
                (14, 14), (13, 13), (12, 12), (11, 11), (10, 10),
                # Big suited cards
                (14, 13, True), (14, 12, True), (14, 11, True), (13, 12, True),
                # Big unsuited cards
                (14, 13, False), (14, 12, False), (13, 12, False)
            ]
            
            # Check for pocket pairs
            if self.hole_cards[0].rank == self.hole_cards[1].rank:
                rank_value = self.hole_cards[0].rank.value
                if (rank_value, rank_value) in premium_hands:
                    return 0.8 + 0.2 * (rank_value - 10) / 4  # 0.8 to 1.0
                else:
                    return 0.4 + 0.4 * (rank_value - 2) / 8  # 0.4 to 0.8
            
            # Check for suited cards
            suited = self.hole_cards[0].suit == self.hole_cards[1].suit
            
            # Calculate the strength based on ranks
            high_rank = max(self.hole_cards[0].rank.value, self.hole_cards[1].rank.value)
            low_rank = min(self.hole_cards[0].rank.value, self.hole_cards[1].rank.value)
            
            # Check if this is a premium hand
            if (high_rank, low_rank, suited) in premium_hands:
                return 0.7 + 0.1 * (high_rank - 11) / 3  # 0.7 to 0.8
            
            # Connected cards (consecutive ranks) are stronger
            connected = high_rank - low_rank == 1
            
            # Base strength on high card and gap
            gap = high_rank - low_rank
            strength = 0.2 + 0.3 * (high_rank - 2) / 12 - 0.05 * gap
            
            # Bonus for suited and connected
            if suited:
                strength += 0.1
            if connected:
                strength += 0.1
            
            return max(0.1, min(strength, 0.6))  # Cap non-premium hands at 0.6 preflop
        
        # Postflop evaluation based on all available cards
        all_cards = self.hole_cards + self.community_cards
        rank, _ = HandEvaluator.evaluate(all_cards)
        
        # Map hand ranks to strength values
        hand_rank_strength: Dict[HandRank, float] = {
            HandRank.HIGH_CARD: 0.1,
            HandRank.ONE_PAIR: 0.3,
            HandRank.TWO_PAIR: 0.5,
            HandRank.THREE_OF_A_KIND: 0.7,
            HandRank.STRAIGHT: 0.8,
            HandRank.FLUSH: 0.85,
            HandRank.FULL_HOUSE: 0.9,
            HandRank.FOUR_OF_A_KIND: 0.95,
            HandRank.STRAIGHT_FLUSH: 0.98,
            HandRank.ROYAL_FLUSH: 1.0
        }
        
        return hand_rank_strength[rank]
    
    def get_action(self, game_state: GameState) -> Tuple[PlayerAction, Optional[int]]:
        """Choose an action based on a tight-aggressive strategy.
        
        Args:
            game_state: Current state of the game
            
        Returns:
            A tuple containing the action and the bet amount (if applicable)
        """
        # Get the current player state
        player_state = game_state.players[self.player_id]
        
        # Get the current highest bet
        current_highest_bet = max(p.current_bet for p in game_state.players.values())
        
        # Calculate how much more we need to call
        call_amount = current_highest_bet - player_state.current_bet
        
        # Evaluate hand strength
        hand_strength = self._evaluate_hand_strength()
        
        # Tight-aggressive strategy: play few hands but play them strongly
        if hand_strength < 0.4:
            # Weak hand: check if possible, otherwise fold
            if call_amount == 0:
                return PlayerAction.CHECK, None
            else:
                # Occasionally bluff with a weak hand in late position
                if random.random() < 0.05:
                    bet_amount = game_state.big_blind * 2
                    return PlayerAction.RAISE, min(bet_amount, player_state.stack)
                else:
                    return PlayerAction.FOLD, None
        elif hand_strength < 0.6:
            # Medium hand: call small bets, fold to big bets
            if call_amount == 0:
                # Sometimes bet with a medium hand
                if random.random() < 0.4:
                    bet_amount = game_state.big_blind * 2
                    return PlayerAction.BET, min(bet_amount, player_state.stack)
                else:
                    return PlayerAction.CHECK, None
            elif call_amount <= game_state.big_blind * 3:
                return PlayerAction.CALL, call_amount
            else:
                return PlayerAction.FOLD, None
        else:
            # Strong hand: bet or raise aggressively
            if call_amount == 0:
                # No one has bet, make a bet
                bet_amount = int(game_state.big_blind * (3 + hand_strength * 3))
                return PlayerAction.BET, min(bet_amount, player_state.stack)
            else:
                # Someone has bet, raise with strong hands
                if hand_strength > 0.7:
                    raise_factor = 2 + int(hand_strength * 2)  # 2-4x raise
                    raise_amount = min(call_amount * raise_factor, player_state.stack)
                    return PlayerAction.RAISE, raise_amount
                else:
                    # Just call with decent hands
                    return PlayerAction.CALL, call_amount
