"""
Settings management for Robot Hold 'Em using dotenv.
"""
import os
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# OpenAI API settings
OPENAI_API_KEY: Optional[str] = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL: str = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

# Game settings
STARTING_STACK: int = int(os.environ.get("STARTING_STACK", "1000"))
SMALL_BLIND: int = int(os.environ.get("SMALL_BLIND", "5"))
BIG_BLIND: int = int(os.environ.get("BIG_BLIND", "10"))
BROADCAST_MODE: bool = os.environ.get("BROADCAST_MODE", "True").lower() == "true"

# Number of hands to play in demo mode
NUM_HANDS: int = int(os.environ.get("NUM_HANDS", "3"))

# Debug mode - when True, displays LLM prompts
DEBUG: bool = os.environ.get("DEBUG", "False").lower() == "true"
