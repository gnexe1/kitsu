# POPAL — Personal AI Computer Agent

POPAL is a cross-platform personal AI computer agent designed to work as a highly capable desktop assistant. It provides a clean, modular, and secure foundation for natural language computer control.

> **Phase 0 does NOT contain AI, voice, vision, or gesture control.**
> This release establishes the foundational architecture only.

## Project Goals

POPAL is being built incrementally. The long-term vision includes:

- Voice control and speech-to-text
- Natural language command understanding
- Computer vision and screen awareness
- Hand/finger gesture control
- Keyboard and mouse automation
- Application-level interaction
- File and system management
- Cross-platform support (Windows + Linux)
- Long-term memory and learning
- AI planning and reasoning
- Strict safety and permission controls
- Verification of every important action

## Architecture

```
Voice Input
    |
Speech-to-Text (Phase 1+)
    |
AI Brain (Phase 2+)
    |
Intent / Plan
    |
Command Validation
    |
Safety Engine
    |
Permission Check
    |
Confirmation (if required)
    |
Tool System
    |
Platform Adapter
    |
Windows / Linux
    |
Verification
```

The AI never directly executes OS commands. All actions go through POPAL's controlled tool system with safety checks.

### Module Structure

```
src/popal/
├── core/          Command processing, execution, routing, state
├── safety/        Policies, permissions, confirmation
├── tools/         Base tool interface, registry, built-in tools
├── platform/      OS detection, Windows/Linux adapters
├── ai/            Brain and planner (placeholder)
├── voice/         Speech recognition (placeholder)
├── vision/        Computer vision (placeholder)
├── gestures/      Hand/gesture control (placeholder)
├── memory/        SQLite database foundation
├── cli/           Command-line interface
└── utils/         Logging, configuration, errors
```

## Installation

### Requirements

- Python 3.12+
- pip

### Install

```bash
cd POPAL
pip install -e .
```

Or with dev dependencies:

```bash
pip install -e ".[dev]"
```

## Running POPAL

### As a module

```bash
python -m popal
```

### As a CLI command

```bash
popal
```

### CLI Commands

| Command | Description |
|---------|-------------|
| `help` | Show available commands |
| `status` | Display current POPAL status |
| `tools` | List registered tools |
| `stop` | Trigger emergency stop |
| `resume` | Resume from emergency stop |
| `exit` / `quit` | Leave POPAL |

### Tool Commands

| Command | Description |
|---------|-------------|
| `system_info` | Retrieve system information |
| `open_application <name>` | Open an application |
| `close_application <name>` | Close an application |
| `list_applications` | List running applications |

## Safety Model

POPAL implements a multi-layer safety pipeline:

1. **Command Validation** — Every command must have a valid intent and structure.
2. **Risk Classification** — Tools declare their risk level: `SAFE`, `CONTROLLED`, or `DESTRUCTIVE`.
3. **Safety Policy** — Evaluates whether the tool is allowed based on risk level and configuration.
4. **Permission Check** — Verifies the current session has permission for the operation.
5. **Confirmation** — Controlled and destructive actions require explicit user confirmation.
6. **Emergency Stop** — A global stop mechanism that halts all command execution.

No tool can bypass these checks. The AI will never have unrestricted access to the operating system.

## Configuration

POPAL uses `config/config.yaml` for all settings:

```yaml
popal:
  name: "POPAL"
  environment: "development"
  log_level: "INFO"

platform:
  auto_detect: true

safety:
  confirmation_required: true
  emergency_stop_enabled: true

logging:
  enabled: true
  directory: "data/logs"
```

## Platform Support

| Platform | Status |
|----------|--------|
| Ubuntu/Linux | Supported |
| Windows | Supported (adapter present) |
| Other Linux distros | Architecture allows future support |

Platform detection is automatic and returns structured information about the OS, distribution, and architecture.

## Running Tests

```bash
pytest
```

Or with verbose output:

```bash
pytest -v
```

## Development Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| **Phase 0** | Foundation and system architecture | Current |
| Phase 1 | Voice system (speech-to-text) | Planned |
| Phase 2 | AI brain integration | Planned |
| Phase 3 | Computer vision | Planned |
| Phase 4 | Gesture control | Planned |
| Phase 5 | Advanced memory and learning | Planned |

## License

MIT License — see [LICENSE](LICENSE).