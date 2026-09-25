# POPAL — Personal AI Computer Agent

POPAL is a cross-platform personal AI computer agent designed to work as a highly capable desktop assistant. It provides a clean, modular, and secure foundation for natural language computer control.

## What's New in Phase 1

Phase 1 adds a complete **voice interface** with push-to-talk activation:

- **Microphone capture** via sounddevice (PortAudio)
- **Voice Activity Detection** via Silero VAD (with energy-based fallback)
- **Speech-to-text** via faster-whisper (local, offline, CPU-based)
- **Deterministic command parser** with configurable app aliases
- **Text-to-speech** via pyttsx3
- **Voice session manager** orchestrating the full pipeline
- All voice commands pass through the existing safety/executor pipeline

> Wake-word detection ("Hey Popal") is experimental — no custom model exists.
> Push-to-talk is the primary activation method.

## Project Goals

POPAL is being built incrementally. The long-term vision includes:

- ~~Voice control and speech-to-text~~ (Phase 1)
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
Voice Input (Microphone)
    |
VAD (Voice Activity Detection)
    |
STT (Speech-to-Text)
    |
Deterministic Command Parser
    |
Structured Command
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
TTS Response
```

All voice commands pass through POPAL's existing safety pipeline. The AI never directly executes OS commands.

### Module Structure

```
src/popal/
├── core/          Command processing, execution, routing, state
├── safety/        Policies, permissions, confirmation
├── tools/         Base tool interface, registry, built-in tools
├── platform/      OS detection, Windows/Linux adapters
├── ai/            Brain and planner (placeholder)
├── voice/         Voice system (Phase 1)
│   ├── providers/    Concrete implementations
│   │   ├── audio_device_provider.py   Sounddevice device manager
│   │   ├── microphone_provider.py     Microphone capture
│   │   ├── silero_vad_provider.py     Silero VAD
│   │   ├── faster_whisper_stt.py      Whisper STT
│   │   ├── pyttsx3_tts.py            Text-to-speech
│   │   ├── oww_wake_word.py          OpenWakeWord (experimental)
│   │   └── deterministic_parser.py    Command parser
│   ├── session.py     Voice session manager
│   ├── types.py       Data types (VoiceState, TranscriptionResult, etc.)
│   ├── errors.py      Voice-specific errors
│   └── [interface].py Abstract interfaces
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
- PortAudio library (`libportaudio2` on Ubuntu/Debian)

### Install

```bash
cd POPAL
pip install -e .
```

With voice support:

```bash
pip install -e ".[voice]"
```

With dev dependencies:

```bash
pip install -e ".[dev,voice]"
```

### Ubuntu/Debian system dependency

```bash
sudo apt install libportaudio2
```

### Faster Whisper model download

The first time you use voice, faster-whisper will download the STT model (~150MB for "base"). This happens automatically.

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

### Voice Commands (Phase 1)

| Command | Description |
|---------|-------------|
| `voice devices` | List audio input devices |
| `voice test` | Test microphone recording |
| `voice listen` | Push-to-talk: record, transcribe, and execute |
| `voice stop` | Stop voice session |
| `voice status` | Show voice system status |

### Supported Voice Phrases

| Phrase | Action |
|--------|--------|
| "Open VS Code" | Opens Visual Studio Code |
| "Open Firefox" | Opens Firefox |
| "Close Chrome" | Closes Google Chrome |
| "List applications" | Lists running apps |
| "System info" | Shows system information |
| "Hey Popal, open terminal" | Opens terminal (strips wake word) |

## Safety Model

POPAL implements a multi-layer safety pipeline:

1. **Command Validation** — Every command must have a valid intent and structure.
2. **Risk Classification** — Tools declare their risk level: `SAFE`, `CONTROLLED`, or `DESTRUCTIVE`.
3. **Safety Policy** — Evaluates whether the tool is allowed based on risk level and configuration.
4. **Permission Check** — Verifies the current session has permission for the operation.
5. **Confirmation** — Controlled and destructive actions require explicit user confirmation.
6. **Emergency Stop** — A global stop mechanism that halts all command execution.

Voice-specific safety:
- Transcribed speech is treated as untrusted input.
- Empty or low-confidence transcripts are rejected.
- Unknown commands are not executed.
- All voice commands pass through the same safety pipeline as CLI commands.
- Audio is not saved to disk by default.

## Configuration

POPAL uses `config/config.yaml` for all settings. Voice configuration includes microphone device, STT model, language, VAD settings, TTS options, wake-word settings, timeouts, and privacy controls.

## Platform Support

| Platform | Status |
|----------|--------|
| Ubuntu/Linux | Supported (tested) |
| Windows | Adapter present, voice untested |
| Other Linux distros | Architecture allows future support |

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
| **Phase 0** | Foundation and system architecture | Complete |
| **Phase 1** | Voice system (speech-to-text) | Current |
| Phase 2 | AI brain integration | Planned |
| Phase 3 | Computer vision | Planned |
| Phase 4 | Gesture control | Planned |
| Phase 5 | Advanced memory and learning | Planned |

## License

MIT License — see [LICENSE](LICENSE).