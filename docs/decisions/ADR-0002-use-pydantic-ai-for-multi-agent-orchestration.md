# ADR-0002: Use Pydantic AI for Multi-Agent Orchestration

## Status

Implemented

## Context

The project originally used Google ADK (Agent Development Kit) with regex-based intent classification for the AI chat assistant. This approach was brittle -- regex patterns couldn't handle nuanced user intent, and maintaining a growing list of patterns became a constant burden. Any new capability required adding more regex rules, and edge cases were impossible to cover reliably.

Google ADK itself proved problematic. Its API was unstable across releases, documentation was sparse and often outdated, and the single monolithic agent file (`adk_agent.py`) had grown to 113KB. The combination of fragile routing and an unreliable framework made the chat assistant difficult to extend and test.

The project needed an agent framework that supported structured output for intent classification, multiple AI providers (Anthropic, OpenAI, Gemini, Ollama), and clean separation between routing logic and domain-specific agent behavior.

## Decision

Replace Google ADK and regex routing with **Pydantic AI** agents and a structured LLM router. The architecture follows a dispatch pattern:

1. **RouterAgent** receives the user message and produces a `RoutingDecision` via structured output -- no regex involved.
2. **Orchestrator** dispatches to the appropriate sub-agent (ConfigAgent, InvestigationAgent, ReportAgent) based on the routing decision. Supports single, chain, and parallel execution modes.
3. **Sub-agents** each have access to 11 shared async tool functions defined in `agent_tools.py`.

Key implementation details:

- `pydantic-ai >= 1.0.0` as the agent framework dependency.
- `Agent(output_type=RoutingDecision)` for structured intent classification -- the LLM returns typed data, not free text.
- Model+Provider pattern for all providers: `AnthropicModel(name, provider=AnthropicProvider(api_key=...))` supporting Anthropic, OpenAI, Gemini, and Ollama (local).
- `TestModel()` from `pydantic_ai.models.test` for unit tests -- no real LLM calls needed.
- Lazy agent factories in the orchestrator enable easy monkeypatching in tests.
- Ollama can't do structured output, so a fallback keyword router handles local models.

## Alternatives Considered

| Alternative | Reason Rejected |
|-------------|-----------------|
| Google ADK | Unstable API, poor documentation, led to a 113KB monolithic agent file |
| LangChain | Too heavy, too many abstractions for our use case |
| Custom LLM wrapper | More control but would need to build tool calling, structured output, and retry logic from scratch |
| Regex intent routing | Brittle, couldn't handle nuanced queries, required constant maintenance |

## Consequences

**Pros:**
- Type-safe structured routing via Pydantic models -- intent classification is validated at the type level
- Fully testable without LLM calls using `TestModel()`
- Clean separation of concerns: router, orchestrator, sub-agents, and tools are all independent
- Multi-provider support out of the box (Anthropic, OpenAI, Gemini, Ollama)
- Tool calling via simple decorators rather than manual function registration

**Cons:**
- Pydantic AI is relatively new, with risk of API changes in future versions
- Ollama can't do structured output, requiring a separate fallback keyword routing path
- Team needs to learn Pydantic AI patterns (agents, tools, dependency injection)

## References

- Migration plan: `docs/superpowers/plans/2026-03-11-pydantic-ai-migration.md`
- Key files: `services/orchestrator.py`, `services/agents/router.py`, `services/agent_tools.py`, `services/agent_factory.py`
- Branch: `feat/agents/multi-orchestration-agents`
