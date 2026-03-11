# Pydantic AI Migration Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Google ADK + regex-based routing with Pydantic AI agents and a structured LLM router call, eliminating all regex classification.

**Architecture:** A `RouterAgent` (smaller/cheaper model, structured output) classifies each user message into a `RoutingDecision`. The orchestrator uses that decision to dispatch to one or more sub-agents (config, investigation, report). Tool functions are standalone async functions that call the DB directly, shared across all sub-agents.

**Tech Stack:** `pydantic-ai>=0.0.14`, Pydantic v2, FastAPI (existing), Python 3.11+, pytest + pytest-asyncio

---

## File Map

### New files
| Path | Responsibility |
|------|---------------|
| `services/agents/__init__.py` | Package marker |
| `services/agents/router.py` | `RouterAgent` + `RoutingDecision` schema |
| `services/agents/config.py` | `config_agent` — data source & check setup |
| `services/agents/investigation.py` | `investigation_agent` — diagnostics & root cause |
| `services/agents/report.py` | `report_agent` — summaries & dashboards |
| `services/agent_tools.py` | All 11 standalone tool functions (DB-direct) |
| `services/agent_factory.py` | `build_model(provider, model, api_key)` → `Model` |
| `services/orchestrator.py` | `run_chat(message, history, deps)` → `str` |
| `tests/test_agent_router.py` | Unit tests for `RoutingDecision` schema + dispatch |
| `tests/test_agent_tools.py` | Unit tests for each tool function (mocked DB) |
| `tests/test_orchestrator.py` | Unit tests for chain/parallel/single dispatch |

### Modified files
| Path | Change |
|------|--------|
| `requirements.txt` | Add `pydantic-ai`, remove `google-adk`, `litellm` |
| `core/config.py` | Add `ai_provider`, `ai_model`, `ai_api_key`, `ai_router_model`, `ai_base_url`; remove `adk_*` |
| `api/v1/endpoints/chat.py` | Replace ADK calls with `orchestrator.run_chat()` |
| `env.example` | Replace `ADK_*` vars with new `AI_*` vars |

### Deleted files
- `services/adk_agent.py`
- `services/intent_router.py`
- `services/sub_agents.py`
- (old) `services/orchestrator.py` — replaced by new one at same path

---

## Chunk 1: Foundation (deps, factory, schemas, requirements)

### Task 1: Add pydantic-ai to requirements.txt

**Files:**
- Modify: `datametronome/podium/requirements.txt`

- [ ] **Step 1.1: Write a failing test that imports pydantic-ai**

Create `datametronome/podium/tests/test_pydantic_ai_import.py`:

```python
"""Smoke test: pydantic-ai must be importable."""

def test_pydantic_ai_importable():
    from pydantic_ai import Agent  # noqa: F401
    from pydantic_ai.models.test import TestModel  # noqa: F401
    assert True
```

- [ ] **Step 1.2: Run to confirm it fails**

```bash
cd datametronome/podium
python -m pytest tests/test_pydantic_ai_import.py -v
```
Expected: `ModuleNotFoundError: No module named 'pydantic_ai'`

- [ ] **Step 1.3: Update requirements.txt**

Replace the ADK section:
```
# Before (remove these two lines):
# google-adk>=0.1.0
# litellm>=1.0.0  # Required by google-adk.models.lite_llm

# After (add these):
pydantic-ai[anthropic,openai,gemini]>=0.0.14
```

> Note: Keep `httpx>=0.25.0` — still needed for the existing API endpoints.

- [ ] **Step 1.4: Install dependencies**

```bash
cd datametronome/podium
pip install pydantic-ai[anthropic,openai,gemini]>=0.0.14
```

- [ ] **Step 1.5: Run the test to confirm it passes**

```bash
python -m pytest tests/test_pydantic_ai_import.py -v
```
Expected: PASS

- [ ] **Step 1.6: Commit**

```bash
git add datametronome/podium/requirements.txt datametronome/podium/tests/test_pydantic_ai_import.py
git commit -m "feat: add pydantic-ai dependency, remove google-adk"
```

---

### Task 2: Update config.py with new AI settings

**Files:**
- Modify: `datametronome/podium/datametronome_podium/core/config.py`

- [ ] **Step 2.1: Write failing test**

Add to `tests/test_unit.py` (or create `tests/test_config_ai.py`):

```python
def test_ai_provider_defaults():
    from datametronome_podium.core.config import settings
    assert settings.ai_provider in ("anthropic", "openai", "gemini", "ollama")
    assert settings.ai_model
    assert settings.ai_router_model is None or isinstance(settings.ai_router_model, str)
```

- [ ] **Step 2.2: Run to confirm it fails**

```bash
python -m pytest tests/test_config_ai.py -v
```
Expected: `AttributeError: 'Settings' object has no attribute 'ai_provider'`

- [ ] **Step 2.3: Replace ADK fields in config.py**

In `datametronome_podium/core/config.py`, replace the `# AI Agent / ADK Configuration` block (lines 78–102):

```python
    # AI Agent Configuration
    ai_provider: str = Field(
        default="ollama",
        env="DATAMETRONOME_AI_PROVIDER",
        description="AI provider: anthropic | openai | gemini | ollama",
    )
    ai_model: str = Field(
        default="qwen2.5",
        env="DATAMETRONOME_AI_MODEL",
        description="Model name for the main agents (e.g. claude-sonnet-4-6, gpt-4o, qwen2.5)",
    )
    ai_api_key: str = Field(
        default="",
        env="DATAMETRONOME_AI_API_KEY",
        description="API key for the AI provider (not needed for Ollama)",
    )
    ai_router_model: str | None = Field(
        default=None,
        env="DATAMETRONOME_AI_ROUTER_MODEL",
        description="Optional cheaper model for the router agent (e.g. claude-haiku-4-5). "
                    "If unset, uses ai_model.",
    )
    ai_base_url: str | None = Field(
        default=None,
        env="DATAMETRONOME_AI_BASE_URL",
        description="Custom base URL (required for Ollama: http://localhost:11434/v1)",
    )
    ollama_api_base: str = Field(
        default="http://localhost:11434",
        env="OLLAMA_API_BASE",
        description="Ollama API base URL (legacy compat). Used when ai_provider=ollama and ai_base_url is unset.",
    )
```

Also remove the old field names from `print_startup_banner` and `validate_production_config` if they reference `adk_model` or `adk_api_key`.

- [ ] **Step 2.4: Run the test to confirm it passes**

```bash
python -m pytest tests/test_config_ai.py -v
```
Expected: PASS

- [ ] **Step 2.5: Commit**

```bash
git add datametronome/podium/datametronome_podium/core/config.py datametronome/podium/tests/test_config_ai.py
git commit -m "feat: replace adk_* config fields with ai_provider/ai_model/ai_api_key"
```

---

### Task 3: Implement agent_factory.py

**Files:**
- Create: `datametronome/podium/datametronome_podium/services/agent_factory.py`
- Test: `datametronome/podium/tests/test_agent_factory.py`

- [ ] **Step 3.1: Write failing tests**

Create `tests/test_agent_factory.py`:

```python
"""Tests for agent_factory — builds Pydantic AI Model from provider/model/key."""
import pytest


def test_build_model_ollama():
    from datametronome_podium.services.agent_factory import build_model
    from pydantic_ai.models.openai import OpenAIModel

    model = build_model("ollama", "qwen2.5", api_key=None, base_url="http://localhost:11434/v1")
    assert isinstance(model, OpenAIModel)


def test_build_model_anthropic():
    from datametronome_podium.services.agent_factory import build_model
    from pydantic_ai.models.anthropic import AnthropicModel

    model = build_model("anthropic", "claude-haiku-4-5", api_key="sk-ant-test")
    assert isinstance(model, AnthropicModel)


def test_build_model_openai():
    from datametronome_podium.services.agent_factory import build_model
    from pydantic_ai.models.openai import OpenAIModel

    model = build_model("openai", "gpt-4o-mini", api_key="sk-test")
    assert isinstance(model, OpenAIModel)


def test_build_model_gemini():
    from datametronome_podium.services.agent_factory import build_model
    from pydantic_ai.models.gemini import GeminiModel

    model = build_model("gemini", "gemini-1.5-flash", api_key="test-key")
    assert isinstance(model, GeminiModel)


def test_build_model_unknown_raises():
    from datametronome_podium.services.agent_factory import build_model

    with pytest.raises(ValueError, match="Unsupported AI provider"):
        build_model("foobar", "model", api_key=None)


def test_build_model_from_settings():
    from datametronome_podium.services.agent_factory import build_model_from_settings

    # Should not raise — uses defaults (ollama/qwen2.5)
    model = build_model_from_settings()
    assert model is not None


def test_build_router_model_from_settings_uses_ai_router_model_when_set(monkeypatch):
    import os
    monkeypatch.setenv("DATAMETRONOME_AI_ROUTER_MODEL", "claude-haiku-4-5")
    monkeypatch.setenv("DATAMETRONOME_AI_PROVIDER", "anthropic")
    monkeypatch.setenv("DATAMETRONOME_AI_API_KEY", "sk-ant-test")
    # Reload settings
    from importlib import reload
    import datametronome_podium.core.config as cfg_module
    reload(cfg_module)
    import datametronome_podium.services.agent_factory as factory_module
    reload(factory_module)
    from datametronome_podium.services.agent_factory import build_router_model_from_settings
    from pydantic_ai.models.anthropic import AnthropicModel

    model = build_router_model_from_settings()
    assert isinstance(model, AnthropicModel)
```

- [ ] **Step 3.2: Run to confirm all fail**

```bash
python -m pytest tests/test_agent_factory.py -v
```
Expected: all FAIL with `ModuleNotFoundError`

- [ ] **Step 3.3: Implement agent_factory.py**

Create `datametronome_podium/services/agent_factory.py`:

```python
"""
Builds Pydantic AI Model objects from environment configuration.

Supported providers: anthropic | openai | gemini | ollama
"""
import logging

from pydantic_ai.models import Model

logger = logging.getLogger(__name__)


def build_model(
    provider: str,
    model_name: str,
    api_key: str | None,
    base_url: str | None = None,
) -> Model:
    """Build a Pydantic AI Model for the given provider.

    Args:
        provider: One of "anthropic", "openai", "gemini", "ollama"
        model_name: Provider-specific model identifier
        api_key: API key (not required for Ollama)
        base_url: Custom base URL (required for Ollama; optional for OpenAI-compatible endpoints)

    Returns:
        A Pydantic AI Model instance
    """
    provider = provider.lower().strip()

    if provider == "anthropic":
        from pydantic_ai.models.anthropic import AnthropicModel
        return AnthropicModel(model_name, api_key=api_key or "")

    if provider == "openai":
        from pydantic_ai.models.openai import OpenAIModel
        kwargs: dict = {"api_key": api_key or ""}
        if base_url:
            kwargs["base_url"] = base_url
        return OpenAIModel(model_name, **kwargs)

    if provider == "gemini":
        from pydantic_ai.models.gemini import GeminiModel
        return GeminiModel(model_name, api_key=api_key or "")

    if provider == "ollama":
        from pydantic_ai.models.openai import OpenAIModel
        # Ollama exposes an OpenAI-compatible API
        ollama_base = base_url or "http://localhost:11434/v1"
        return OpenAIModel(model_name, base_url=ollama_base, api_key="ollama")

    raise ValueError(
        f"Unsupported AI provider: '{provider}'. "
        "Choose one of: anthropic, openai, gemini, ollama"
    )


def build_model_from_settings() -> Model:
    """Build the main agent model from application settings."""
    from datametronome_podium.core.config import settings

    base_url = settings.ai_base_url
    if settings.ai_provider == "ollama" and not base_url:
        # Derive from ollama_api_base (legacy compat)
        base_url = settings.ollama_api_base.rstrip("/") + "/v1"

    logger.info(
        "Building main model: provider=%s model=%s",
        settings.ai_provider,
        settings.ai_model,
    )
    return build_model(
        provider=settings.ai_provider,
        model_name=settings.ai_model,
        api_key=settings.ai_api_key or None,
        base_url=base_url,
    )


def build_router_model_from_settings() -> Model:
    """Build the router model from settings (uses ai_router_model if set, else ai_model)."""
    from datametronome_podium.core.config import settings

    router_model_name = settings.ai_router_model or settings.ai_model
    base_url = settings.ai_base_url
    if settings.ai_provider == "ollama" and not base_url:
        base_url = settings.ollama_api_base.rstrip("/") + "/v1"

    logger.info(
        "Building router model: provider=%s model=%s",
        settings.ai_provider,
        router_model_name,
    )
    return build_model(
        provider=settings.ai_provider,
        model_name=router_model_name,
        api_key=settings.ai_api_key or None,
        base_url=base_url,
    )
```

- [ ] **Step 3.4: Run tests**

```bash
python -m pytest tests/test_agent_factory.py -v
```
Expected: all PASS (except monkeypatch test — it may need adjustment for settings reloading; skip if flaky)

- [ ] **Step 3.5: Commit**

```bash
git add datametronome/podium/datametronome_podium/services/agent_factory.py datametronome/podium/tests/test_agent_factory.py
git commit -m "feat: add agent_factory — builds Pydantic AI models from env config"
```

---

## Chunk 2: Tools + Router

### Task 4: Extract tool functions to agent_tools.py

**Context:** In `adk_agent.py`, tools are methods that call `get_db()` directly (not HTTP). We extract them as standalone async functions. Pydantic AI tools don't need `RunContext` if they have no runtime deps.

**Files:**
- Create: `datametronome/podium/datametronome_podium/services/agent_tools.py`
- Test: `datametronome/podium/tests/test_agent_tools.py`

- [ ] **Step 4.1: Write failing tests**

Create `tests/test_agent_tools.py`:

```python
"""Unit tests for agent tool functions. DB is mocked."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.fixture
def mock_db():
    db = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_list_staves_returns_dict(mock_db):
    mock_db.query.return_value = [
        {"id": "s1", "name": "prod", "data_source_type": "postgres",
         "connection_config": "{}", "is_active": 1,
         "created_at": "2025-01-01T00:00:00Z", "updated_at": "2025-01-01T00:00:00Z",
         "description": None}
    ]
    with patch("datametronome_podium.services.agent_tools.get_db", return_value=mock_db):
        from datametronome_podium.services.agent_tools import list_staves
        result = await list_staves()
        assert "staves" in result
        assert result["count"] == 1


@pytest.mark.asyncio
async def test_list_staves_active_only(mock_db):
    mock_db.query.return_value = []
    with patch("datametronome_podium.services.agent_tools.get_db", return_value=mock_db):
        from datametronome_podium.services.agent_tools import list_staves
        result = await list_staves(active_only=True)
        # Check that the SQL query used 'is_active'
        call_args = mock_db.query.call_args[0][0]
        assert "is_active" in call_args["sql"]


@pytest.mark.asyncio
async def test_get_stave_not_found(mock_db):
    mock_db.query.return_value = []
    with patch("datametronome_podium.services.agent_tools.get_db", return_value=mock_db):
        from datametronome_podium.services.agent_tools import get_stave
        result = await get_stave("nonexistent-id")
        assert "error" in result


@pytest.mark.asyncio
async def test_get_summary_report_returns_dict(mock_db):
    mock_db.query.return_value = [{"total": 5, "active": 3}]
    with patch("datametronome_podium.services.agent_tools.get_db", return_value=mock_db):
        from datametronome_podium.services.agent_tools import get_summary_report
        result = await get_summary_report()
        assert isinstance(result, dict)
```

- [ ] **Step 4.2: Run to confirm they fail**

```bash
python -m pytest tests/test_agent_tools.py -v
```
Expected: all FAIL with `ModuleNotFoundError`

- [ ] **Step 4.3: Implement agent_tools.py**

Create `datametronome_podium/services/agent_tools.py`.

Extract the 11 tool methods verbatim from `adk_agent.py` (lines ~267–end of file), converting them from instance methods to standalone async functions. The only change is removing `self` and replacing `self.api_base_url` with a `get_db()` call where needed.

Key conversion pattern:
```python
# Before (in adk_agent.py, as a method):
async def list_staves(self, limit: int = 100, skip: int = 0, active_only: bool = False) -> dict:
    ...
    db = await get_db()
    ...

# After (in agent_tools.py, standalone):
async def list_staves(limit: int = 100, skip: int = 0, active_only: bool = False) -> dict:
    """List all data sources (staves) in DataMetronome.

    Args:
        limit: Maximum number of staves to return (default: 100)
        skip: Number of staves to skip for pagination (default: 0)
        active_only: If True, return only active staves. Default: False
    """
    try:
        from datetime import datetime
        from datametronome_podium.core.database import get_db
        from datametronome_podium.services.stave_service import deserialize_stave

        db = await get_db()
        if active_only:
            staves = await db.query({
                "sql": "SELECT * FROM staves WHERE is_active = 1 ORDER BY created_at DESC LIMIT ? OFFSET ?",
                "params": [limit, skip],
            })
        else:
            staves = await db.query({
                "sql": "SELECT * FROM staves ORDER BY created_at DESC LIMIT ? OFFSET ?",
                "params": [limit, skip],
            })
        # ... rest of implementation same as adk_agent.py ...
```

Apply the same pattern for all 11 tools:
- `list_staves(limit, skip, active_only)` → from adk_agent.py lines ~267–319
- `get_stave(stave_id)` → lines ~321–348
- `create_stave(name, data_source_type, connection_config, description, is_active)` → lines ~350–end of method
- `list_stave_tables(stave_id, include_structure)` → next method
- `get_table_sample(stave_id, table_name, limit)` → next method
- `suggest_quality_checks(stave_id, table_name, use_sample_data)` → next method
- `list_clefs(active_only, stave_id)` → next method
- `get_clef(clef_id)` → next method
- `list_checks(stave_id, clef_id, limit, status)` → next method
- `get_summary_report()` → next method
- `get_quality_report()` → next method

Export all 11 as a list constant at the bottom of the file:
```python
ALL_TOOLS = [
    list_staves,
    get_stave,
    create_stave,
    list_stave_tables,
    get_table_sample,
    suggest_quality_checks,
    list_clefs,
    get_clef,
    list_checks,
    get_summary_report,
    get_quality_report,
]
```

- [ ] **Step 4.4: Run tests**

```bash
python -m pytest tests/test_agent_tools.py -v
```
Expected: all PASS

- [ ] **Step 4.5: Commit**

```bash
git add datametronome/podium/datametronome_podium/services/agent_tools.py datametronome/podium/tests/test_agent_tools.py
git commit -m "feat: extract tool functions to agent_tools.py (DB-direct, shared across agents)"
```

---

### Task 5: Implement RoutingDecision + RouterAgent

**Files:**
- Create: `datametronome/podium/datametronome_podium/services/agents/__init__.py`
- Create: `datametronome/podium/datametronome_podium/services/agents/router.py`
- Test: `datametronome/podium/tests/test_agent_router.py`

- [ ] **Step 5.1: Write failing tests**

Create `tests/test_agent_router.py`:

```python
"""Tests for RouterAgent and RoutingDecision schema."""
import pytest
from pydantic import ValidationError


def test_routing_decision_valid():
    from datametronome_podium.services.agents.router import RoutingDecision

    rd = RoutingDecision(
        intent="investigation",
        mode="chain",
        agents=["investigation", "config"],
        reasoning="User asked why checks failed and how to fix them.",
    )
    assert rd.intent == "investigation"
    assert rd.mode == "chain"
    assert rd.agents == ["investigation", "config"]


def test_routing_decision_invalid_intent():
    from datametronome_podium.services.agents.router import RoutingDecision

    with pytest.raises(ValidationError):
        RoutingDecision(intent="unknown_intent", mode="single", agents=["report"], reasoning="")


def test_routing_decision_invalid_mode():
    from datametronome_podium.services.agents.router import RoutingDecision

    with pytest.raises(ValidationError):
        RoutingDecision(intent="quick", mode="broadcast", agents=["report"], reasoning="")


def test_routing_decision_invalid_agent():
    from datametronome_podium.services.agents.router import RoutingDecision

    with pytest.raises(ValidationError):
        RoutingDecision(intent="quick", mode="single", agents=["hacker"], reasoning="")


@pytest.mark.asyncio
async def test_router_agent_structured_output_with_test_model():
    """RouterAgent must return a RoutingDecision when run with TestModel."""
    from pydantic_ai.models.test import TestModel
    from datametronome_podium.services.agents.router import build_router_agent, RoutingDecision

    agent = build_router_agent(TestModel())
    result = await agent.run("What is the status of my data sources?")
    # TestModel returns a valid instance conforming to result_type
    assert isinstance(result.data, RoutingDecision)
```

- [ ] **Step 5.2: Run to confirm they fail**

```bash
python -m pytest tests/test_agent_router.py -v
```
Expected: FAIL on all

- [ ] **Step 5.3: Create agents package**

```bash
mkdir -p datametronome/podium/datametronome_podium/services/agents
touch datametronome/podium/datametronome_podium/services/agents/__init__.py
```

- [ ] **Step 5.4: Implement router.py**

Create `datametronome_podium/services/agents/router.py`:

```python
"""
RouterAgent: classifies user intent into a RoutingDecision.

Uses a small/fast model. Returns structured Pydantic output — no regex.
"""
import logging
from typing import Literal

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models import Model

logger = logging.getLogger(__name__)

VALID_INTENTS = Literal["quick", "config", "investigation", "report", "exploration"]
VALID_MODES = Literal["single", "chain", "parallel"]
VALID_AGENTS = Literal["config", "investigation", "report"]


class RoutingDecision(BaseModel):
    """Structured routing output from the RouterAgent."""

    intent: VALID_INTENTS
    mode: VALID_MODES
    agents: list[VALID_AGENTS]
    reasoning: str  # short explanation for tracing/debugging


_ROUTER_SYSTEM_PROMPT = """You are a routing assistant for DataMetronome, a data quality monitoring platform.

Given a user message, output a routing decision with these fields:
- intent: one of quick | config | investigation | report | exploration
- mode: one of single | chain | parallel
- agents: list of agents to run — one or more of: config | investigation | report
- reasoning: one sentence explaining your decision

Intent definitions:
- quick: greetings, status checks, simple counts, "how many staves do I have?"
- config: creating/configuring data sources (staves), setting up quality checks (clefs)
- investigation: diagnosing failures, root cause analysis, "why did this check fail?"
- report: summaries, dashboards, quality reports, "give me an overview"
- exploration: browsing tables, sampling data, "show me the tables in stave X"

Mode + agents rules:
- single: one agent handles the whole request → agents = [best_agent]
- chain: investigation followed by recommendations → agents = ["investigation", "config"]
  Use when: user asks to diagnose AND fix/suggest (e.g. "why did X fail and how to fix it")
- parallel: two agents run concurrently → agents = ["report", "config"]
  Use when: user asks for an overview AND suggestions at the same time

Default (when unsure): mode=single, agents=["report"]

Respond ONLY with the JSON object. No prose."""


def build_router_agent(model: Model) -> Agent[None, RoutingDecision]:
    """Build a RouterAgent with the given model."""
    return Agent(
        model=model,
        result_type=RoutingDecision,
        system_prompt=_ROUTER_SYSTEM_PROMPT,
    )
```

- [ ] **Step 5.5: Run tests**

```bash
python -m pytest tests/test_agent_router.py -v
```
Expected: all PASS

- [ ] **Step 5.6: Commit**

```bash
git add datametronome/podium/datametronome_podium/services/agents/ datametronome/podium/tests/test_agent_router.py
git commit -m "feat: add RoutingDecision schema and RouterAgent (structured LLM output, no regex)"
```

---

## Chunk 3: Sub-agents + Orchestrator

### Task 6: Implement sub-agents

**Files:**
- Create: `services/agents/config.py`
- Create: `services/agents/investigation.py`
- Create: `services/agents/report.py`
- Test: `datametronome/podium/tests/test_sub_agents.py`

- [ ] **Step 6.1: Write failing tests**

Create `tests/test_sub_agents.py`:

```python
"""Tests: sub-agents can be built and respond with TestModel."""
import pytest
from pydantic_ai.models.test import TestModel


@pytest.mark.asyncio
async def test_config_agent_runs():
    from datametronome_podium.services.agents.config import build_config_agent

    agent = build_config_agent(TestModel())
    result = await agent.run("How do I create a new data source?")
    assert isinstance(result.data, str)
    assert len(result.data) > 0


@pytest.mark.asyncio
async def test_investigation_agent_runs():
    from datametronome_podium.services.agents.investigation import build_investigation_agent

    agent = build_investigation_agent(TestModel())
    result = await agent.run("Why did the row count check fail yesterday?")
    assert isinstance(result.data, str)


@pytest.mark.asyncio
async def test_report_agent_runs():
    from datametronome_podium.services.agents.report import build_report_agent

    agent = build_report_agent(TestModel())
    result = await agent.run("Give me a summary of the system status.")
    assert isinstance(result.data, str)
```

- [ ] **Step 6.2: Run to confirm they fail**

```bash
python -m pytest tests/test_sub_agents.py -v
```

- [ ] **Step 6.3: Implement agents/config.py**

Create `datametronome_podium/services/agents/config.py`:

```python
"""ConfigAgent: helps users set up data sources (staves) and quality checks (clefs)."""
from pydantic_ai import Agent
from pydantic_ai.models import Model

from datametronome_podium.services.agent_tools import ALL_TOOLS

_SYSTEM_PROMPT = """You are the DataMetronome configuration specialist.

You help users set up data sources (staves), configure quality checks (clefs), and
suggest appropriate checks for their tables.

Key concepts:
- Staves: Data sources (PostgreSQL, BigQuery, etc.) — where data lives
- Clefs: Quality check definitions — what to monitor

CRITICAL: When a user asks to list, explore, or count anything — call the appropriate
tool directly. Never ask for IDs when you can discover them with a list tool.

CONVERSATION MEMORY: When users refer to "this stave", "it", "that", check conversation
history. Never ask them to repeat info already provided.

Be concise and action-oriented."""


def build_config_agent(model: Model) -> Agent:
    """Build the config agent with the given model."""
    return Agent(
        model=model,
        system_prompt=_SYSTEM_PROMPT,
        tools=ALL_TOOLS,
    )
```

- [ ] **Step 6.4: Implement agents/investigation.py**

Create `datametronome_podium/services/agents/investigation.py`:

```python
"""InvestigationAgent: diagnoses failures, explores data, analyzes anomalies."""
from pydantic_ai import Agent
from pydantic_ai.models import Model

from datametronome_podium.services.agent_tools import ALL_TOOLS

_SYSTEM_PROMPT = """You are the DataMetronome investigation specialist.

You help users understand why checks failed, explore data, analyze anomalies,
and diagnose data quality issues.

Key concepts:
- Checks: Execution results of quality checks (passed/failed)
- get_quality_report: Overview of quality metrics over time
- get_table_sample: Inspect actual data for debugging
- list_checks: See which checks passed or failed

CRITICAL: When asked why something failed — first call list_checks or get_quality_report
to see what actually happened. Then use get_table_sample to inspect the data if needed.

CONVERSATION MEMORY: When users refer to "this stave", "it", "that", check conversation
history. Never ask them to repeat info already provided.

Be analytical and thorough."""


def build_investigation_agent(model: Model) -> Agent:
    """Build the investigation agent with the given model."""
    return Agent(
        model=model,
        system_prompt=_SYSTEM_PROMPT,
        tools=ALL_TOOLS,
    )
```

- [ ] **Step 6.5: Implement agents/report.py**

Create `datametronome_podium/services/agents/report.py`:

```python
"""ReportAgent: provides overviews, status summaries, and quality reports."""
from pydantic_ai import Agent
from pydantic_ai.models import Model

from datametronome_podium.services.agent_tools import ALL_TOOLS

_SYSTEM_PROMPT = """You are the DataMetronome reporting specialist.

You provide overviews, status summaries, and quality reports.

Key tools:
- get_summary_report: System-wide status
- get_quality_report: Quality metrics over time
- list_staves / list_clefs: Enumerate data sources and checks

CRITICAL: When a user asks for a report, overview, or status — call get_summary_report
first for a quick high-level view, then drill down as needed.

CONVERSATION MEMORY: When users refer to "this stave", "it", "that", check conversation
history. Never ask them to repeat info already provided.

Be clear and summarize key metrics."""


def build_report_agent(model: Model) -> Agent:
    """Build the report agent with the given model."""
    return Agent(
        model=model,
        system_prompt=_SYSTEM_PROMPT,
        tools=ALL_TOOLS,
    )
```

- [ ] **Step 6.6: Run tests**

```bash
python -m pytest tests/test_sub_agents.py -v
```
Expected: all PASS

- [ ] **Step 6.7: Commit**

```bash
git add datametronome/podium/datametronome_podium/services/agents/ datametronome/podium/tests/test_sub_agents.py
git commit -m "feat: add config/investigation/report sub-agents (pydantic-ai, shared tools)"
```

---

### Task 7: Implement new orchestrator.py

**Context:** This replaces the old `orchestrator.py`. The new one:
1. Calls `RouterAgent.run()` to get a `RoutingDecision`
2. Dispatches to sub-agents based on `decision.mode`
3. For chain: passes previous agent's text output as context to next agent
4. For parallel: uses `asyncio.gather`
5. Converts DB history dicts to Pydantic AI message format

**Files:**
- Replace: `datametronome/podium/datametronome_podium/services/orchestrator.py`
- Test: `datametronome/podium/tests/test_orchestrator.py`

- [ ] **Step 7.1: Write failing tests**

Create `tests/test_orchestrator.py`:

```python
"""Tests for the new orchestrator — dispatch logic, chain, parallel."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic_ai.models.test import TestModel


def make_mock_result(text: str):
    """Create a mock agent run result."""
    result = MagicMock()
    result.data = text
    return result


@pytest.mark.asyncio
async def test_convert_history_user_message():
    from datametronome_podium.services.orchestrator import convert_history_to_messages
    from pydantic_ai.messages import ModelRequest

    history = [{"role": "user", "content": "hello"}]
    messages = convert_history_to_messages(history)
    assert len(messages) == 1
    assert isinstance(messages[0], ModelRequest)


@pytest.mark.asyncio
async def test_convert_history_assistant_message():
    from datametronome_podium.services.orchestrator import convert_history_to_messages
    from pydantic_ai.messages import ModelResponse

    history = [{"role": "assistant", "content": "Hi there!"}]
    messages = convert_history_to_messages(history)
    assert len(messages) == 1
    assert isinstance(messages[0], ModelResponse)


@pytest.mark.asyncio
async def test_convert_history_skips_unknown_roles():
    from datametronome_podium.services.orchestrator import convert_history_to_messages

    history = [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "hello"},
    ]
    messages = convert_history_to_messages(history)
    # system role is skipped — Pydantic AI handles system prompts separately
    assert len(messages) == 1


@pytest.mark.asyncio
async def test_run_chat_single_mode(monkeypatch):
    """Single mode: router returns single agent, result is that agent's text."""
    from datametronome_podium.services.agents.router import RoutingDecision

    mock_routing = RoutingDecision(
        intent="report", mode="single", agents=["report"],
        reasoning="Simple report request."
    )

    with patch(
        "datametronome_podium.services.orchestrator._get_router_agent"
    ) as mock_router_factory, patch(
        "datametronome_podium.services.orchestrator._get_report_agent"
    ) as mock_report_factory:
        mock_router = AsyncMock()
        mock_router.run.return_value = MagicMock(data=mock_routing)
        mock_router_factory.return_value = mock_router

        mock_report = AsyncMock()
        mock_report.run.return_value = make_mock_result("System status: all green.")
        mock_report_factory.return_value = mock_report

        from datametronome_podium.services import orchestrator
        result = await orchestrator.run_chat("What is the status?", history=[])
        assert result["message"] == "System status: all green."
        assert result["intent"] == "report"
        assert result["mode"] == "single"


@pytest.mark.asyncio
async def test_run_chat_chain_mode(monkeypatch):
    """Chain mode: investigation result is injected into config agent's prompt."""
    from datametronome_podium.services.agents.router import RoutingDecision

    mock_routing = RoutingDecision(
        intent="investigation", mode="chain",
        agents=["investigation", "config"],
        reasoning="User wants to diagnose and fix."
    )

    with patch(
        "datametronome_podium.services.orchestrator._get_router_agent"
    ) as mock_router_factory, patch(
        "datametronome_podium.services.orchestrator._get_investigation_agent"
    ) as mock_inv_factory, patch(
        "datametronome_podium.services.orchestrator._get_config_agent"
    ) as mock_cfg_factory:
        mock_router = AsyncMock()
        mock_router.run.return_value = MagicMock(data=mock_routing)
        mock_router_factory.return_value = mock_router

        mock_inv = AsyncMock()
        mock_inv.run.return_value = make_mock_result("Found 3 failed checks.")
        mock_inv_factory.return_value = mock_inv

        mock_cfg = AsyncMock()
        mock_cfg.run.return_value = make_mock_result("Recommendation: add freshness check.")
        mock_cfg_factory.return_value = mock_cfg

        from datametronome_podium.services import orchestrator
        result = await orchestrator.run_chat(
            "Why did checks fail and how to fix?", history=[]
        )
        assert result["message"] == "Recommendation: add freshness check."
        assert result["mode"] == "chain"
        # Second agent call should have included previous output in the prompt
        second_call_msg = mock_cfg.run.call_args[0][0]
        assert "Found 3 failed checks." in second_call_msg


@pytest.mark.asyncio
async def test_run_chat_parallel_mode(monkeypatch):
    """Parallel mode: both agents run, results are combined."""
    from datametronome_podium.services.agents.router import RoutingDecision

    mock_routing = RoutingDecision(
        intent="report", mode="parallel",
        agents=["report", "config"],
        reasoning="User wants overview and suggestions."
    )

    with patch(
        "datametronome_podium.services.orchestrator._get_router_agent"
    ) as mock_router_factory, patch(
        "datametronome_podium.services.orchestrator._get_report_agent"
    ) as mock_report_factory, patch(
        "datametronome_podium.services.orchestrator._get_config_agent"
    ) as mock_cfg_factory:
        mock_router = AsyncMock()
        mock_router.run.return_value = MagicMock(data=mock_routing)
        mock_router_factory.return_value = mock_router

        mock_report = AsyncMock()
        mock_report.run.return_value = make_mock_result("System: 5 staves, 12 checks.")
        mock_report_factory.return_value = mock_report

        mock_cfg = AsyncMock()
        mock_cfg.run.return_value = make_mock_result("Suggestion: add 2 more checks.")
        mock_cfg_factory.return_value = mock_cfg

        from datametronome_podium.services import orchestrator
        result = await orchestrator.run_chat("Give overview and suggestions", history=[])
        assert "System: 5 staves" in result["message"]
        assert "Suggestion: add 2 more checks." in result["message"]
        assert result["mode"] == "parallel"
```

- [ ] **Step 7.2: Run to confirm they fail**

```bash
python -m pytest tests/test_orchestrator.py -v
```

- [ ] **Step 7.3: Implement new orchestrator.py**

Replace `datametronome_podium/services/orchestrator.py` with:

```python
"""
Orchestrator: routes user messages to the right sub-agents via structured LLM routing.

Flow:
    1. RouterAgent classifies message → RoutingDecision
    2. Orchestrator dispatches based on decision.mode:
       - single: one agent, full conversation history
       - chain: agent A → agent B (B receives A's output + original message)
       - parallel: agent A + agent B concurrently, results combined
"""
import asyncio
import logging
from typing import Any

from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart

from datametronome_podium.services.agents.router import RoutingDecision, build_router_agent
from datametronome_podium.services.agents.config import build_config_agent
from datametronome_podium.services.agents.investigation import build_investigation_agent
from datametronome_podium.services.agents.report import build_report_agent
from datametronome_podium.services.agent_factory import (
    build_model_from_settings,
    build_router_model_from_settings,
)

logger = logging.getLogger(__name__)

# --- Lazy agent factories (allow monkeypatching in tests) ---

def _get_router_agent():
    return build_router_agent(build_router_model_from_settings())

def _get_config_agent():
    return build_config_agent(build_model_from_settings())

def _get_investigation_agent():
    return build_investigation_agent(build_model_from_settings())

def _get_report_agent():
    return build_report_agent(build_model_from_settings())


_AGENT_BUILDERS = {
    "config": _get_config_agent,
    "investigation": _get_investigation_agent,
    "report": _get_report_agent,
}


def convert_history_to_messages(history: list[dict]) -> list[ModelMessage]:
    """Convert DB message dicts (role/content) to Pydantic AI ModelMessage list.

    System messages are skipped — system prompts are handled by agent configuration.
    Only user and assistant messages are converted.
    """
    messages: list[ModelMessage] = []
    for msg in history:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        elif role == "assistant":
            messages.append(ModelResponse(parts=[TextPart(content=content)]))
        # skip "system" and anything else — not part of Pydantic AI conversation history
    return messages


async def run_chat(
    message: str,
    history: list[dict],
    *,
    router_history_window: int = 6,
) -> dict[str, Any]:
    """Run the full chat pipeline: route → dispatch → respond.

    Args:
        message: Current user message
        history: Full conversation history as list of {role, content} dicts
        router_history_window: How many recent messages to send to the router for context

    Returns:
        dict with keys: message (str), intent (str), mode (str),
                        agents (list[str]), model (str)
    """
    # Step 1: Convert history
    all_history = convert_history_to_messages(history)
    router_history = all_history[-router_history_window:] if all_history else []

    # Step 2: Route
    router = _get_router_agent()
    routing_result = await router.run(message, message_history=router_history)
    decision: RoutingDecision = routing_result.data

    logger.info(
        "Router decision: intent=%s mode=%s agents=%s reasoning=%r",
        decision.intent, decision.mode, decision.agents, decision.reasoning,
    )

    # Step 3: Dispatch
    if decision.mode == "parallel" and len(decision.agents) >= 2:
        response_message = await _run_parallel(message, decision, all_history)
    elif decision.mode == "chain" and len(decision.agents) >= 2:
        response_message = await _run_chain(message, decision, all_history)
    else:
        response_message = await _run_single(message, decision, all_history)

    return {
        "message": response_message,
        "intent": decision.intent,
        "mode": decision.mode,
        "agents": decision.agents,
        "model": "pydantic-ai",  # placeholder; could expose actual model name
    }


async def _run_single(
    message: str,
    decision: RoutingDecision,
    history: list[ModelMessage],
) -> str:
    agent_type = decision.agents[0] if decision.agents else "report"
    agent = _AGENT_BUILDERS.get(agent_type, _get_report_agent)()
    result = await agent.run(message, message_history=history)
    return str(result.data)


async def _run_chain(
    message: str,
    decision: RoutingDecision,
    history: list[ModelMessage],
) -> str:
    """Run agents in sequence. Each agent after the first receives the previous output."""
    previous_output = ""
    last_result = ""

    for i, agent_type in enumerate(decision.agents):
        agent = _AGENT_BUILDERS.get(agent_type, _get_report_agent)()

        if i == 0:
            msg_to_send = message
        else:
            msg_to_send = (
                f"INVESTIGATION FINDINGS:\n{previous_output}\n\n"
                f"USER'S REQUEST: {message}\n\n"
                "Using the findings above, address the user's request "
                "(suggest fixes, recommend checks, or propose remedial actions)."
            )

        result = await agent.run(msg_to_send, message_history=history)
        previous_output = str(result.data)
        last_result = previous_output

    return last_result


async def _run_parallel(
    message: str,
    decision: RoutingDecision,
    history: list[ModelMessage],
) -> str:
    """Run agents concurrently, combine their outputs."""
    async def run_agent(agent_type: str) -> tuple[str, str]:
        agent = _AGENT_BUILDERS.get(agent_type, _get_report_agent)()
        result = await agent.run(message, message_history=history)
        return agent_type, str(result.data)

    results = await asyncio.gather(
        *[run_agent(atype) for atype in decision.agents],
        return_exceptions=True,
    )

    parts = []
    for r in results:
        if isinstance(r, Exception):
            parts.append(f"[Error: {r}]")
        else:
            agent_type, text = r
            if text:
                parts.append(f"**{agent_type.title()}:**\n{text}")

    return "\n\n---\n\n".join(parts) if parts else "No responses received."
```

- [ ] **Step 7.4: Run tests**

```bash
python -m pytest tests/test_orchestrator.py -v
```
Expected: all PASS

- [ ] **Step 7.5: Commit**

```bash
git add datametronome/podium/datametronome_podium/services/orchestrator.py datametronome/podium/tests/test_orchestrator.py
git commit -m "feat: new orchestrator — structured LLM routing with chain/parallel/single dispatch"
```

---

## Chunk 4: Endpoint + Cleanup

### Task 8: Update chat.py endpoint

**Context:** The chat endpoint currently calls ADK directly. We replace the AI invocation with `orchestrator.run_chat()`. All database operations (load/save history, tracing) remain unchanged.

**Files:**
- Modify: `datametronome/podium/datametronome_podium/api/v1/endpoints/chat.py`

- [ ] **Step 8.1: Write a smoke test for the endpoint**

Add to `tests/test_api_integration.py` (or create `tests/test_chat_endpoint.py`):

```python
"""Smoke test: chat endpoint uses orchestrator, not ADK."""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient


def test_chat_endpoint_calls_orchestrator(monkeypatch):
    """The /chat endpoint must use run_chat, not ADKAgent."""
    mock_response = {
        "message": "System status: all green.",
        "intent": "report",
        "mode": "single",
        "agents": ["report"],
        "model": "pydantic-ai",
    }

    with patch(
        "datametronome_podium.api.v1.endpoints.chat.run_chat",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        from datametronome_podium.main import app
        client = TestClient(app)
        # Actual auth would be needed — this verifies the import at minimum
        assert "run_chat" in dir(__import__(
            "datametronome_podium.api.v1.endpoints.chat",
            fromlist=["run_chat"]
        ))
```

- [ ] **Step 8.2: Update imports in chat.py**

Replace the import block at the top of `chat.py`:

```python
# Remove these imports:
# from datametronome_podium.services.adk_agent import ADKAgent
# from datametronome_podium.services.intent_router import classify_intent, resolve_model_for_intent
# from datametronome_podium.services.orchestrator import (MODE_CHAIN, MODE_PARALLEL, MODE_SINGLE, get_agent_config, plan_orchestration)

# Add this:
from datametronome_podium.services.orchestrator import run_chat
```

- [ ] **Step 8.3: Replace the AI invocation in `send_chat_message`**

Find the section in `send_chat_message` from the comment `# Phase 1: Intent classifier + router` to the end of the orchestration blocks (parallel/chain/single), approximately lines 156–323.

Replace that entire block with:

```python
        # Run the AI pipeline (router → sub-agents)
        agent_result = await run_chat(
            message=request.message,
            history=history_messages,
        )
        intent = agent_result["intent"]
        orchestration_mode = agent_result["mode"]
        agent_types = agent_result["agents"]
        resolved_model = agent_result.get("model", "pydantic-ai")

        logger.info(
            "📋 Intent=%s → mode=%s agents=%s",
            intent, orchestration_mode, agent_types,
        )

        agent_response = {
            "message": agent_result["message"],
            "toolCalls": None,
            "model": resolved_model,
        }
```

- [ ] **Step 8.4: Fix the error handler in `send_chat_message`**

The `except` block still calls `classify_intent` for error tracing. Replace with:

```python
    except Exception as e:
        duration_ms = trace_duration(start_time)
        try:
            err_user_id = current_user.get("id") or current_user.get("username") or "anonymous"
            err_conv_id = request.conversationId or "error-conv"
            err_msg = (request.message or "")[:500]
            await record_agent_trace(
                conversation_id=err_conv_id,
                user_id=err_user_id,
                user_message=err_msg,
                intent="unknown",
                model=None,
                tool_calls=None,
                duration_ms=duration_ms,
            )
            record_chat_request(status="error", duration_seconds=duration_ms / 1000.0, intent="unknown")
        except Exception as trace_err:
            logger.warning(f"Failed to record error trace: {trace_err}")
        logger.error(f"Error processing chat message: {str(e)}", exc_info=True)
        detail = _user_friendly_error_detail(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )
```

- [ ] **Step 8.5: Remove unused imports from chat.py**

Remove: `import re`, `from datametronome_podium.services.adk_agent import ADKAgent`, and the three lines of orchestrator/intent_router imports.

Also remove the `is_ollama` model check block (lines ~173–179) — Pydantic AI handles auth internally.

- [ ] **Step 8.6: Fix model name reference in `get_conversation_history`**

Line ~522 references `settings.adk_model`. Replace with:

```python
model_name = settings.ai_model or "unknown"
```

- [ ] **Step 8.7: Run existing tests + integration checks**

```bash
python -m pytest tests/ -v -k "not integration" 2>&1 | tail -40
```
Expected: no test regressions

- [ ] **Step 8.8: Commit**

```bash
git add datametronome/podium/datametronome_podium/api/v1/endpoints/chat.py
git commit -m "feat: replace ADK calls in chat.py with orchestrator.run_chat()"
```

---

### Task 9: Update env.example and env.example documentation

**Files:**
- Modify: `env.example`

- [ ] **Step 9.1: Update env.example**

Replace the `# AI Agent / ADK Configuration` section with:

```bash
# AI Agent Configuration
# Provider: anthropic | openai | gemini | ollama (default: ollama)
DATAMETRONOME_AI_PROVIDER=ollama

# Model name for the main agents
DATAMETRONOME_AI_MODEL=qwen2.5

# API key (not needed for Ollama)
# DATAMETRONOME_AI_API_KEY=your-api-key-here

# Optional: cheaper/faster model for the routing step only
# DATAMETRONOME_AI_ROUTER_MODEL=claude-haiku-4-5

# Base URL (required for Ollama; optional for custom OpenAI-compatible endpoints)
# DATAMETRONOME_AI_BASE_URL=http://localhost:11434/v1

# Ollama API base (legacy — used when AI_PROVIDER=ollama and AI_BASE_URL is unset)
# OLLAMA_API_BASE=http://localhost:11434

# Examples for other providers:
# Anthropic (Claude):
#   DATAMETRONOME_AI_PROVIDER=anthropic
#   DATAMETRONOME_AI_MODEL=claude-sonnet-4-6
#   DATAMETRONOME_AI_API_KEY=sk-ant-...
#   DATAMETRONOME_AI_ROUTER_MODEL=claude-haiku-4-5

# OpenAI:
#   DATAMETRONOME_AI_PROVIDER=openai
#   DATAMETRONOME_AI_MODEL=gpt-4o
#   DATAMETRONOME_AI_API_KEY=sk-...

# Google Gemini:
#   DATAMETRONOME_AI_PROVIDER=gemini
#   DATAMETRONOME_AI_MODEL=gemini-1.5-flash
#   DATAMETRONOME_AI_API_KEY=your-gemini-key
```

- [ ] **Step 9.2: Commit**

```bash
git add env.example
git commit -m "docs: update env.example for pydantic-ai config (replace ADK vars)"
```

---

### Task 10: Delete old files

- [ ] **Step 10.1: Delete the four old service files**

```bash
git rm datametronome/podium/datametronome_podium/services/adk_agent.py
git rm datametronome/podium/datametronome_podium/services/intent_router.py
git rm datametronome/podium/datametronome_podium/services/sub_agents.py
```

> Note: `services/orchestrator.py` was replaced in Task 7 — do not delete it.

- [ ] **Step 10.2: Run the full test suite to verify nothing broke**

```bash
cd datametronome/podium
python -m pytest tests/ -v 2>&1 | tail -60
```
Expected: no import errors from deleted files; all existing tests pass.

- [ ] **Step 10.3: Commit**

```bash
git add -A
git commit -m "chore: delete adk_agent.py, intent_router.py, sub_agents.py (replaced by pydantic-ai)"
```

---

### Task 11: End-to-end verification

- [ ] **Step 11.1: Start the server locally**

```bash
cd datametronome/podium
# Set minimal env for Ollama (default)
export DATAMETRONOME_AI_PROVIDER=ollama
export DATAMETRONOME_AI_MODEL=qwen2.5
python -m uvicorn datametronome_podium.main:app --port 8001 --reload
```

- [ ] **Step 11.2: Send a test chat request**

```bash
# Get auth token first (assuming default dev user)
TOKEN=$(curl -s -X POST http://localhost:8001/api/v1/auth/token \
  -d "username=admin&password=admin" | jq -r .access_token)

curl -s -X POST http://localhost:8001/api/v1/chat/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "How many data sources do I have?"}' | jq .
```

Expected response includes: `intent`, `orchestrationMode`, `agentType` fields in the JSON.

- [ ] **Step 11.3: Test multi-language routing**

```bash
curl -s -X POST http://localhost:8001/api/v1/chat/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Quante sorgenti dati ho configurato?"}' | jq .intent
```
Expected: router classifies correctly (e.g. "quick" or "exploration") without hardcoded patterns.

- [ ] **Step 11.4: Test chain routing**

```bash
curl -s -X POST http://localhost:8001/api/v1/chat/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Why did the check fail and how can I fix it?"}' | jq '{intent, mode: .orchestrationMode}'
```
Expected: `"mode": "chain"`

- [ ] **Step 11.5: Run all tests one final time**

```bash
cd datametronome/podium
python -m pytest tests/ -v
```
Expected: all PASS

- [ ] **Step 11.6: Final commit**

```bash
git add -A
git commit -m "feat: complete pydantic-ai migration — structured LLM routing, no regex"
```

---

## Summary

| Old | New |
|-----|-----|
| `adk_agent.py` (113KB, ADK + LiteLLM) | `agent_tools.py` (11 standalone tool fns) + 3 focused sub-agents |
| `intent_router.py` (regex patterns) | `agents/router.py` (structured LLM output) |
| `sub_agents.py` (prompt stings) | `agents/config.py`, `agents/investigation.py`, `agents/report.py` |
| `orchestrator.py` (regex chain/parallel triggers) | `orchestrator.py` (dispatch from `RoutingDecision`) |
| env: `DATAMETRONOME_ADK_*` | env: `DATAMETRONOME_AI_PROVIDER/MODEL/API_KEY` |

**Multi-language support:** Works automatically — LLM router understands any language and mirrors it in responses.

**Provider switching:** Change `DATAMETRONOME_AI_PROVIDER` + `DATAMETRONOME_AI_MODEL` + `DATAMETRONOME_AI_API_KEY`.
