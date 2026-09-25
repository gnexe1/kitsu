# POPAL — Personal AI Computer Agent

POPAL is a cross-platform personal AI computer agent designed to work as a highly capable desktop assistant.

## What's New in Phase 3

Phase 3 adds the **AI Brain** — a safe, structured reasoning and planning layer:

- **AI Provider abstraction** — pluggable providers (local, future: OpenAI, Anthropic, Ollama)
- **Local deterministic provider** — regex-based, fully offline, no API key required
- **Structured command schema** — strict validation of intents, parameters, confidence
- **Multi-step plans** — sequential command plans with configurable step limits
- **Plan validation** — schema, intent, parameter, dangerous-pattern checks
- **Ambiguity handling** — clarification/rejection for unsupported requests
- **Response formatter** — natural-language responses based on actual execution results
- **Context system** — bounded, safe context (no secrets/screenshots/recordings)
- **Prompt injection resistance** — model output treated as untrusted
- All AI commands pass through the existing safety/executor pipeline

### AI Pipeline

```
Natural Language Request
    |
AI Provider (local/OpenAI/Anthropic)
    |
Structured JSON Output
    |
Schema Validation → Dangerous Pattern Check
    |
Intent + Parameter Validation
    |
Existing Safety Engine
    |
Existing Permission + Confirmation
    |
Tool Registry + Executor
    |
Verified Result → Natural Language Response
```

The AI Brain is POPAL's **thinking** layer — the existing safety/tool architecture remains POPAL's **hands and security system**.

## Architecture

```
Voice Input → STT → Deterministic Parser → Command Pipeline
                      ↓ (fallback)
                   AI Brain → Structured Plan → Validation → Safety → Execution
```

### Module Structure

```
src/popal/
├── core/          Command processing, execution, routing, state
├── safety/        Policies, permissions, confirmation
├── tools/         Base tool interface, registry
├── platform/      OS detection, Windows/Linux adapters
├── computer/      Mouse, keyboard, screen, window, application control
├── voice/         Voice system (push-to-talk, STT, TTS)
├── ai/            AI Brain (Phase 3)
│   ├── types.py          AICommand, AIPlan, AIResult
│   ├── errors.py         AI-specific errors
│   ├── schemas.py        Intent/parameter schemas
│   ├── validator.py      Schema + dangerous-pattern validation
│   ├── context.py        Bounded safe context
│   ├── provider.py       Abstract AIProvider interface
│   ├── planner.py        Request → AIPlan pipeline
│   ├── response.py       Execution result → natural language
│   └── providers/
│       └── local.py      Deterministic local provider
├── vision/        Computer vision (placeholder)
├── gestures/      Hand/gesture control (placeholder)
├── memory/        SQLite database foundation
├── cli/           Command-line interface
└── utils/         Logging, configuration, errors
```

## Installation

```bash
cd POPAL
pip install -e ".[dev,voice]"
```

## Running POPAL

```bash
python -m popal
```

### CLI Commands — AI Brain

| Command | Description |
|---------|-------------|
| `ai status` | Show AI provider status |
| `ai plan "open VS Code"` | Plan a command (does NOT execute) |
| `ai plan "open VS Code and show system info"` | Plan multi-step |
| `ai execute "open VS Code"` | Plan AND execute through safety pipeline |

## Safety Model

AI-specific safety:
- Schema validation on all AI output
- Intent allowlist (only registered POPAL intents)
- Dangerous pattern detection (`rm -rf`, `sudo`, `os.system()`, etc.)
- Step count limits (configurable, default 10)
- Prompt injection resistance
- Execution verification (responses based on actual tool results)

## Configuration

```yaml
ai:
  enabled: false              # disabled by default
  provider: "local"           # "local" (deterministic), future: "openai", "anthropic"
  max_plan_steps: 10
  max_context_messages: 10
  max_context_chars: 12000
```

## Development Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| **Phase 0** | Foundation and system architecture | Complete |
| **Phase 1** | Voice system (speech-to-text) | Complete |
| **Phase 2** | Computer control foundation | Complete |
| **Phase 3** | AI Brain (reasoning + planning) | Current |
| Phase 4 | Computer vision | Planned |
| Phase 5 | Gesture control | Planned |

## License

MIT License — see [LICENSE](LICENSE).