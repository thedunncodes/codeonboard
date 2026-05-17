"""Run the CodeOnboard MCP server directly."""
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from src.codeonboard.server import run, run_http

if __name__ == "__main__":
    if "--http" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8000
        host = sys.argv[sys.argv.index("--host") + 1] if "--host" in sys.argv else "0.0.0.0"
        run_http(host=host, port=port)
    else:
        run()
