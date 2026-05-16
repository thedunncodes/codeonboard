# Project Documentation Rules (Non-Obvious Only)

## Repository Structure

- **MCP server entry is run_server.py** - Use `python run_server.py`, NOT `python -m src.codeonboard.server` (see `run_server.py:11`)
- **Storage in data/context/** - SQLite database auto-created at `data/context/context.db` on first import (see `config.py:39-40`)
- **Context expires after 24 hours** - Cached repository data automatically expires and is deleted (see `context_store.py:64`)

## Architecture Patterns

- **Three-tool MCP server** - `fetch_repo`, `generate_guide`, `ask_codebase` are the only exposed tools (see `server.py:20-68`)
- **Graceful watsonx degradation** - All watsonx imports wrapped in try/except; server works without credentials (see `tools/generate_guide.py:11-15`)
- **Async-first design** - All tools are async, watsonx SDK calls use `loop.run_in_executor()` (see `generate_guide.py:121`)
- **Context truncation at 80K chars** - Hard limit prevents LLM token overflow, no configuration option (see `context_store.py:129`)

## Non-Standard Conventions

- **File size limit is 4000 chars** - Individual files truncated during fetch, not at read time (see `config.py:47`)
- **Max 40 files per repo** - Hard limit on files fetched to prevent overwhelming system (see `config.py:48`)
- **Pydantic v2 serialization** - Must use `model_dump(mode='json')` for datetime fields (see `context_store.py:58`)
- **GITHUB_TOKEN is required** - Raises `ValueError` immediately if missing, unlike optional watsonx credentials (see `config.py:18`)