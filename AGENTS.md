# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Build & Run

- Run MCP server: `python run_server.py` (NOT `python -m src.codeonboard.server`)
- Test: `pytest tests/` (requires pytest-asyncio for async tests)
- Install: `pip install -e .` for editable install

## Critical Non-Obvious Patterns

- **WatsonX imports are try/except wrapped** - All watsonx imports use try/except to gracefully degrade when credentials missing. Never import watsonx modules directly without this pattern.
- **Context store uses 24-hour expiry** - Cached repo data auto-expires after 24 hours in SQLite (see `context_store.py:64`)
- **Context string has 80K char hard limit** - `get_context_string()` truncates at 80,000 chars to prevent LLM token overflow (see `context_store.py:129`)
- **File content limited to 4000 chars** - Individual files truncated at `MAX_FILE_SIZE=4000` during fetch (see `config.py:47`)
- **Max 40 files fetched per repo** - `MAX_FILES_TO_FETCH=40` prevents overwhelming the system (see `config.py:48`)
- **Async executor pattern for sync watsonx** - WatsonX SDK is synchronous, so use `loop.run_in_executor()` to avoid blocking (see `generate_guide.py:121`)
- **Config raises on missing GITHUB_TOKEN** - Unlike watsonx (which warns), missing `GITHUB_TOKEN` raises `ValueError` immediately (see `config.py:18`)
- **Storage dir auto-created** - `STORAGE_DIR` (data/context/) is created on import, not on first use (see `config.py:40`)
- **RepoTree serialization uses mode='json'** - Must use `model_dump(mode='json')` for datetime serialization in Pydantic v2 (see `context_store.py:58`)

## Environment Variables

Required:
- `GITHUB_TOKEN` - Raises error if missing

Optional (graceful degradation):
- `WATSONX_API_KEY`, `WATSONX_PROJECT_ID`, `WATSONX_URL`
- `WATSONX_MODEL_ID` (default: "meta-llama/llama-3-3-70b-instruct")
- `WATSONX_MAX_TOKENS` (default: 2048)

## Code Style

- All files end with `# Made with Bob` comment
- Async functions use `async def` with proper `await` for I/O operations
- Type hints required for function parameters and returns
- Docstrings use Google style with Args/Returns sections
- Error handling: Specific exceptions with descriptive messages