"""
Personality definitions for LLM-powered commentators in Robot Hold 'Em.
"""
from typing import Dict, Optional

from robot_hold_em.commentators.llm_commentator import LLMCommentator


class CommentatorPersonalities:
    """A collection of predefined personalities for LLM commentators."""
    
    # Predefined personalities
    PERSONALITIES = {
        "professional": "You are a professional poker commentator with deep knowledge of the game. "
                       "You provide insightful analysis of player decisions, pot odds, and strategic implications. "
                       "Your commentary is measured, informative, and focused on the technical aspects of the game.",
        
        "enthusiastic": "You are an enthusiastic poker commentator who gets excited about big pots and bold moves. "
                       "Your commentary is energetic, dramatic, and focused on the excitement of the game. "
                       "You use colorful language and metaphors to describe the action.",
        
        "comedic": "You are a comedic poker commentator who finds humor in the game situations. "
                  "Your commentary is witty, irreverent, and includes jokes and puns. "
                  "You don't take the game too seriously and like to entertain the audience.",
        
        "historical": "You are a poker historian who relates current game situations to famous poker moments. "
                     "Your commentary includes references to poker history, legendary players, and classic hands. "
                     "You provide context and perspective based on the rich history of poker.",
        
        "statistical": "You are a statistics-focused poker commentator who emphasizes probabilities and expected values. "
                      "Your commentary includes percentages, odds, and mathematical analysis. "
                      "You help the audience understand the mathematical underpinnings of poker decisions.",
        
        "dramatic": "You are a dramatic poker commentator who treats each hand like a suspenseful story. "
                   "Your commentary builds tension and emphasizes the psychological aspects of the game. "
                   "You focus on the human drama, the high stakes, and the emotional impact of wins and losses."
    }
    
    @classmethod
    def create_commentator(cls, 
                          commentator_id: str, 
                          name: str, 
                          personality_type: str = "professional", 
                          model: str = "gpt-4o-mini",
                          custom_personality: Optional[str] = None) -> LLMCommentator:
        """Create an LLM commentator with the specified personality.
        
        Args:
            commentator_id: Unique identifier for the commentator
            name: Display name for the commentator
            personality_type: Type of personality to use (must be one of the predefined types)
                              or "custom" to use custom_personality
            model: The OpenAI model to use for commentary generation
            custom_personality: A custom personality description (used only if personality_type is "custom")
            
        Returns:
            An LLMCommentator instance with the specified personality
            
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
        
        return LLMCommentator(commentator_id, name, model, personality)
    
    @classmethod
    def get_available_personalities(cls) -> Dict[str, str]:
        """Get a dictionary of available predefined personalities.
        
        Returns:
            A dictionary mapping personality type names to their descriptions
        """
        return cls.PERSONALITIES.copy()
