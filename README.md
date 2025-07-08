# Robot Hold 'Em

Robot Hold 'Em is a CLI application for playing Texas Hold 'Em poker against multiple robot opponents and a framework for building your own robot opponents.

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/robot-hold-em.git
cd robot-hold-em

# Install dependencies using uv
uv sync
```

## Configuration

Robot Hold 'Em uses environment variables for configuration, loaded via `dotenv`. To set up your environment:

1. Copy the example environment file to create your own:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file to customize your settings:
   ```
   # OpenAI API settings
   OPENAI_API_KEY=your_openai_api_key_here
   OPENAI_MODEL=gpt-4o-mini
   
   # Game settings
   STARTING_STACK=1000
   SMALL_BLIND=5
   BIG_BLIND=10
   BROADCAST_MODE=True
   
   # Number of hands to play in demo mode
   NUM_HANDS=3
   ```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|--------|
| `OPENAI_API_KEY` | Your OpenAI API key | None (required for LLM robot) |
| `OPENAI_MODEL` | OpenAI model to use | `gpt-4o-mini` |
| `STARTING_STACK` | Initial chip stack for each player | 1000 |
| `SMALL_BLIND` | Small blind amount | 5 |
| `BIG_BLIND` | Big blind amount | 10 |
| `BROADCAST_MODE` | Whether to show detailed game commentary | `True` |
| `NUM_HANDS` | Number of hands to play in demo mode | 3 |

