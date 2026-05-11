# AGENTS.md — Nuwa

Nuwa is an async Python AI agent framework (`nuwa` v0.4.9, `requires-python >= 3.10`).  
Source layout: `src/nuwa/`. Package manager: `uv` with `uv.lock`.

## Setup & Dev Commands

```bash
uv sync                          # install all deps including dev group
uv run pytest tests/             # run all tests
uv run pytest tests/test_tool.py # run a single test file
uv run ruff check src/ tests/    # lint (no ruff config — runs defaults)
uv run ruff format src/ tests/   # format
uv run mypy src/                 # typecheck (no mypy config — runs defaults)
uv build                         # build source & wheel distributions
```

- Create a `.env` file with `TEST_API_KEY=<real_key>` before running `test_re_act.py` — the `conftest.py` auto-loads it via `load_dotenv(override=True)`.

## Architecture (packages)

Package layout under `src/nuwa/`:

| Directory | Purpose |
|---|---|
| `agents/` | Agent ABC (`base.py`), `ReActAgent` (`react_agent.py`) |
| `llms/` | `LLM` ABC, `OpenAICompatible` implementation |
| `tools/` | `ToolKit` (decorator-based registry), `Tool`/`ToolEntity` models, MCP adapter |
| `contexts/` | `Context` ABC, `SimpleContext` (no-op stub) |
| `embeddings/` | `EmbeddedEncoder` ABC with caching layer, OpenAI + local Qwen3 backends |
| `compressors/` | `ZSTDCompressor` |
| `hashers/` | `CRC64Hasher` |
| `storages/` | `KVStorage` ABC, `LocalKVStorage` (msgpack to disk) |
| `prompts/` | Fluent builder pattern for system prompts |
| `rerankers/` | Empty stub |

Top-level modules:
- `base.py` — `AsyncClosableContext` (async context manager ABC for resource lifecycle), `ConversationStorage` ABC, `StreamChunk`
- `multi_agent.py` — `MultiRoleAgent` class
- `scheduling_tools.py` — `AlarmManager` singleton + `get_alarm_tool()`
- `web_search_tools.py` — Google/Baidu/Bing Playwright-based search tools
- `vector_store.py` — `VectorBackedStorage` (Qdrant-backed conversation storage)

Public API (`from nuwa import ...`):
- `ConversationStorage`, `StreamChunk`, `ToolKit`, `VectorBackedStorage`

## Key Conventions

- **All async**. Everything inheriting `AsyncClosableContext` supports `async with`.
- **Tools**: Use `ToolKit` with the `@tool` decorator (auto-infers parameter types from type annotations including `Annotated`). Call `toolkit.call_tool()` which uses `json_repair.loads` for fault-tolerant JSON parsing of LLM-generated arguments.
- **LLM per-model**: `OpenAICompatible` binds a model at construction time. Passing a different model via `**kwargs` only logs a warning; create a new instance instead.
- **Streaming**: Despite the warning message in `chat()`, the `stream=True` parameter is silently set to `False` by the client wrapper (LLM callers should handle streaming at the agent level, not pass `stream` to chat).
- **Node hierarchy**: `LLM`, `EmbeddedEncoder`, `Compressor`, `DataHasher`, `KVStorage` all extend `AsyncClosableContext` with `initialize()`/`close()` lifecycle.

## Tests

- Tests live in `tests/` and use `src.nuwa.*` imports (not installed package imports).
- `test_tool.py` — unit tests for `ToolKit` (decorator-based tool registry).
- `test_alarm.py` — unit tests for `AlarmManager`.
- `test_react_agent.py` — unit tests for `ReActAgent` initialization and execute_task contract.
- `test_local_conversation_storage.py` — unit tests for `LocalConversationStorage`.
- `test_search.py` — browser automation tests (Playwright, auto-skipped in CI).

**Test prerequisites**:
- No `uv sync` → all tests fail (no deps installed).
- `.env` with `TEST_API_KEY` → needed by integration tests.
- SOCKS5 proxy at `192.168.31.45:10808` → for `test_search.py`.
- MCP server at `192.168.110.10:12119/mcp` → for MCP integration tests.

## ⚠️ Refactoring In Progress

The project has been partially refactored from flat modules to packages. Remaining items:

- **`multi_agent.py`** — `MultiRoleAgent` now extends `Agent` ABC; `execute_task` is a stub (NotImplementedError). Full multi-role ReAct loop TBD.
- **Docs** (`docs/README.md`, `docs/zh/README.md`) reference the old flat module structure (`from src.nuwa.llm import OpenAI`, `from src.nuwa.re_act import ReActAgent`).

When writing code, use the new package-based imports:
- `from src.nuwa.agents.react_agent import ReActAgent`
- `from src.nuwa.llms.openai_compatible import OpenAICompatible`
- `from src.nuwa.tools import ToolKit` (top-level public API)

## CI Pipeline

GitHub Actions workflow (`.github/workflows/ci.yml`) runs on:
- **Pull requests** (opened, synchronize, reopened)
- **Push to `main`**

Jobs:
- **lint-typecheck**: Ubuntu + Python 3.10 — ruff lint, ruff format check, mypy typecheck
- **test-build** (matrix 3 OS × 4 Python): pytest + `uv build`; Playwright browser tests auto-skipped

Required GitHub Secrets:
- `TEST_API_KEY` — API key for LLM-dependent tests; tests skip automatically if not set

## Other Gotchas

- `VectorBackedStorage.get_embeddings()` returns `[]` — it's a stub (real embedding code is commented out).
- `OpenAICompatible` sets `self._client = None` on close — accessing after close raises `RuntimeError`.
- Playwright browser tools use `channel="msedge"` and `headless=False` — will open visible browser windows.
- Web search tools save screenshots as `google_search.png`, `baidu_search.png`, `bing_search.png` in `CWD`.
- `pytest.ini` enables `log_cli_level = DEBUG` — tests produce very verbose output.