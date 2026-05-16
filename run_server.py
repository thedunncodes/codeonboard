"""Run the CodeOnboard MCP server directly."""
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from src.codeonboard.server import run

if __name__ == "__main__":
    run()

# Made with Bob
