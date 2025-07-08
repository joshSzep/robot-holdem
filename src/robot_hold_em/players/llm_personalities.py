"""
Personality definitions for LLM-powered robot players in Robot Hold 'Em.
"""
from typing import Dict, Optional

from robot_hold_em.players.llm_robot import LLMRobot


class LLMPersonalities:
    """A collection of predefined personalities for LLM robot players."""
    
    # Predefined personalities
    PERSONALITIES = {
        "strategic": "You are a strategic poker player who makes calculated decisions based on hand strength, "
                    "position, and opponent behavior. You're willing to bluff occasionally but prefer solid "
                    "mathematical plays.",
        
        "aggressive": "You are an aggressive poker player who likes to put pressure on opponents. "
                     "You frequently bet and raise to force opponents to make difficult decisions. "
                     "You're not afraid to bluff and will often represent strong hands.",
        
        "conservative": "You are a conservative poker player who prioritizes minimizing risk. "
                       "You typically only play premium hands and avoid marginal situations. "
                       "You rarely bluff and prefer to fold when facing significant aggression unless "
                       "you have a very strong hand.",
        
        "unpredictable": "You are an unpredictable poker player who constantly changes your strategy. "
                        "You mix bluffs with value bets in unexpected ways to confuse opponents. "
                        "You sometimes make unconventional plays to throw opponents off balance.",
        
        "mathematical": "You are a mathematical poker player who makes decisions based strictly on pot odds, "
                       "expected value, and probabilities. You calculate the mathematical correctness of each "
                       "decision and ignore psychological factors. You only bluff when the math suggests it's +EV.",
        
        "observant": "You are an observant poker player who focuses on reading opponents and adapting to their "
                    "tendencies. You pay close attention to betting patterns and adjust your strategy accordingly. "
                    "You're willing to make exploitative plays based on opponent weaknesses."
    }
    
    @classmethod
    def create_robot(cls, 
                     player_id: str, 
                     name: str, 
                     personality_type: str = "strategic", 
                     model: str = "gpt-4o-mini",
                     custom_personality: Optional[str] = None) -> LLMRobot:
        """Create an LLM robot with the specified personality.
        
        Args:
            player_id: Unique identifier for the player
            name: Display name for the player
            personality_type: Type of personality to use (must be one of the predefined types)
                              or "custom" to use custom_personality
            model: The OpenAI model to use for decision making
            custom_personality: A custom personality description (used only if personality_type is "custom")
            
        Returns:
            An LLMRobot instance with the specified personality
            
        Raises:
            ValueError: If personality_type is not recognized and not "custom", or
                       if personality_type is "custom" but custom_personality is None
        """
        if personality_type == "custom":
            if custom_personality is None:
                raise ValueError("custom_personality must be provided when personality_type is 'custom'")
            personality = custom_personality
        elif personality_type in cls.PERSONALITIES:
            personality = cls.PERSONALITIES[personality_type]
        else:
            valid_types = list(cls.PERSONALITIES.keys()) + ["custom"]
            raise ValueError(f"personality_type must be one of {valid_types}, got {personality_type}")
        
        return LLMRobot(player_id, name, model, personality)
    
    @classmethod
    def get_available_personalities(cls) -> Dict[str, str]:
        """Get a dictionary of available predefined personalities.
        
        Returns:
            A dictionary mapping personality type names to their descriptions
        """
        return cls.PERSONALITIES.copy()
