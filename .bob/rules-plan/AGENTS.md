# Project Architecture Rules (Non-Obvious Only)

## System Constraints

- **Context hard limit at 80K chars** - `get_context_string()` truncates at 80,000 characters with no configuration option (see `context_store.py:129`)
- **File size capped at 4000 chars** - Individual files truncated during fetch at `MAX_FILE_SIZE=4000` (see `config.py:47`)
- **Max 40 files per repository** - `MAX_FILES_TO_FETCH=40` prevents system overload (see `config.py:48`)
- **24-hour cache expiry** - Repository data auto-expires after 24 hours in SQLite (see `context_store.py:64`)

## Architectural Decisions

- **Synchronous watsonx wrapped in async** - WatsonX SDK is synchronous, so all calls use `loop.run_in_executor()` to avoid blocking (see `generate_guide.py:121`)
- **Graceful degradation for watsonx** - All watsonx imports wrapped in try/except; server functions without credentials (see `tools/generate_guide.py:11-15`)
- **GITHUB_TOKEN is mandatory** - Unlike optional watsonx credentials, missing `GITHUB_TOKEN` raises `ValueError` immediately (see `config.py:18`)
- **Storage dir created on import** - `STORAGE_DIR` (data/context/) auto-created when config.py loads, not on first use (see `config.py:40`)

## Data Flow Patterns

- **Pydantic v2 datetime serialization** - Must use `model_dump(mode='json')` not `dict()` for datetime fields (see `context_store.py:58`)
- **Three-tool workflow** - `fetch_repo` → `generate_guide` or `ask_codebase` (see `server.py:20-68`)
- **Context summarization at 40K chars** - Large contexts automatically summarized before guide generation (see `generate_guide.py:251`)

## Performance Considerations

- **httpx connection pooling** - GitHub client uses max 20 connections, 10 keepalive (see `github/client.py:48-51`)
- **Binary files skipped** - Extensive list of binary extensions excluded from analysis (see `config.py:63-69`)
- **Skip folders enforced** - node_modules, .git, dist, build, __pycache__, .next, vendor, coverage (see `config.py:51-60`)