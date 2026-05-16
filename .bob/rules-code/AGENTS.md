# Project Coding Rules (Non-Obvious Only)

## Critical Patterns

- **WatsonX imports must use try/except** - All watsonx imports wrapped in try/except for graceful degradation (see `watsonx/summarizer.py:31-34`)
- **Async executor for sync watsonx calls** - WatsonX SDK is synchronous, must use `loop.run_in_executor()` to avoid blocking event loop (see `generate_guide.py:121`)
- **Pydantic v2 datetime serialization** - Use `model_dump(mode='json')` not `dict()` for datetime fields (see `context_store.py:58`)
- **File content truncation at 4000 chars** - `MAX_FILE_SIZE=4000` enforced during fetch, not configurable per-call (see `config.py:47`)
- **Context string 80K hard limit** - `get_context_string()` truncates at 80,000 chars, no exceptions (see `context_store.py:129`)
- **Storage dir created on import** - `STORAGE_DIR` auto-created when config.py loads, not lazily (see `config.py:40`)

## Error Handling

- **GITHUB_TOKEN raises, watsonx warns** - Missing `GITHUB_TOKEN` raises `ValueError`, missing watsonx credentials only warn (see `config.py:18,30`)
- **Specific exceptions required** - Use `ValueError`, `RuntimeError` with descriptive messages, not generic `Exception`

## Code Style

- **All files end with `# Made with Bob`** - Required comment at end of every Python file
- **Google-style docstrings** - Args/Returns sections required for all functions
- **Type hints mandatory** - Function parameters and returns must have type hints

## No Access to MCP/Browser Tools

This mode does not have access to MCP servers or browser automation tools.