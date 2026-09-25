# POPAL — Personal AI Computer Agent

POPAL is a cross-platform personal AI computer agent designed to work as a highly capable desktop assistant.

## What's New in Phase 2

Phase 2 adds the **Computer Control Foundation** — safe, controlled mouse, keyboard, screen, window, and application management:

- **Mouse control** — position, move, click, double-click, right-click, scroll
- **Keyboard control** — type text, press keys, hotkey combinations
- **Screen capture** — full screen and region capture (stays in memory, not saved)
- **Window management** — list, focus, minimize, maximize, restore, close
- **Application control** — open, close, list, focus, running check
- **Input lock** — prevents conflicting concurrent operations
- All actions pass through the existing safety/executor pipeline

### Platform Support

| Capability | Linux (X11/XWayland) | Linux (Wayland native) | Windows |
|------------|---------------------|----------------------|---------|
| Mouse | pynput | Planned (ydotool) | Win32 SendInput |
| Keyboard | pynput | Planned (ydotool) | Win32 SendInput |
| Screenshots | mss | mss | mss |
| Windows | wmctrl + xdotool | Limited | Win32 API |
| Applications | subprocess | subprocess | subprocess |

> Linux: Tested on Ubuntu with XWayland. Window management requires `wmctrl`.
> Windows: Provider exists but is NOT verified on actual Windows hardware.

## Project Goals

- ~~Voice control and speech-to-text~~ (Phase 1)
- ~~Computer control (mouse, keyboard, screen, windows)~~ (Phase 2)
- Natural language command understanding
- Computer vision and screen awareness
- Hand/finger gesture control
- Cross-platform support (Windows + Linux)
- Long-term memory and learning
- AI planning and reasoning
- Strict safety and permission controls

## Architecture

```
Voice Input  →  VAD  →  STT  →  Command Parser
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
                              Tool Registry
                                    |
                       ┌────────────┼────────────┐
                       │            │            │
                   System       Voice       Computer
                   Tools        Tools        Control
                       │            │            │
                  Platform     Microphone    Mouse/KB/Screen
                  Adapter      STT/TTS       Window/App
                       │                       │
                  ┌────┴────┐            ┌─────┴─────┐
                  │         │            │           │
               Linux    Windows       Linux      Windows
```

All commands pass through POPAL's safety pipeline. No unrestricted execution.

### Module Structure

```
src/popal/
├── core/          Command processing, execution, routing, state
├── safety/        Policies, permissions, confirmation
├── tools/         Base tool interface, registry
├── platform/      OS detection, Windows/Linux adapters
├── computer/      Computer control (Phase 2)
│   ├── mouse.py          Abstract mouse interface
│   ├── keyboard.py       Abstract keyboard interface
│   ├── screen.py         Abstract screen interface
│   ├── window.py         Abstract window interface
│   ├── application.py    Abstract application interface
│   ├── tools.py          Computer control tools for registry
│   ├── input_lock.py     Concurrent operation lock
│   ├── types.py          MousePosition, ScreenSize, WindowInfo, etc.
│   ├── errors.py         Error types
│   └── providers/        Platform implementations
│       ├── linux_provider.py    pynput + mss + wmctrl
│       └── windows_provider.py  Win32 APIs (untested)
├── voice/         Voice system (Phase 1)
├── ai/            Brain and planner (placeholder)
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
- `wmctrl` for window management on Linux (`sudo apt install wmctrl`)

### Install

```bash
cd POPAL
pip install -e ".[dev,voice]"
```

Computer control dependencies (pynput, mss) are installed automatically with the voice extras.

## Running POPAL

```bash
python -m popal
# or
popal
```

### CLI Commands — Computer Control

| Command | Description |
|---------|-------------|
| `mouse position` | Get cursor position |
| `mouse move 500 300` | Move cursor to (500, 300) |
| `mouse click` | Left click |
| `mouse double-click` | Double-click |
| `mouse right-click` | Right-click |
| `mouse scroll down` | Scroll down |
| `keyboard type hello world` | Type literal text |
| `keyboard press enter` | Press Enter key |
| `keyboard hotkey ctrl+c` | Press Ctrl+C |
| `screen size` | Get screen dimensions |
| `screen screenshot` | Capture screenshot (in memory) |
| `window list` | List visible windows |
| `window active` | Show active window |

### Supported Voice Phrases (Computer Control)

| Phrase | Action |
|--------|--------|
| "Click" | Left click |
| "Double click" | Double-click |
| "Right click" | Right-click |
| "Move 500 300" | Move mouse to (500, 300) |
| "Scroll down" | Scroll mouse wheel down |
| "Type hello world" | Type literal text |
| "Press enter" | Press Enter key |
| "Take screenshot" | Capture screen |
| "List windows" | Show open windows |

## Safety Model

Computer control risk classifications:

| Risk Level | Tools |
|------------|-------|
| **SAFE** | mouse_position, screen_size, screen_screenshot, window_list, window_active |
| **CONTROLLED** | mouse_move, mouse_click, keyboard_type, keyboard_press, keyboard_hotkey, window_focus/minimize/maximize/restore |
| **DESTRUCTIVE** | window_close |

Additional safety measures:
- Invalid coordinates are rejected
- `type_text()` only types literal text — never executes or presses Enter
- Screenshots stay in memory by default, never saved/uploaded
- Input lock prevents conflicting operations
- Emergency stop halts all computer control

## Configuration

Computer control section in `config/config.yaml`:

```yaml
computer:
  provider: "auto"          # "auto", "linux", "windows"
  screenshot:
    save_to_disk: false     # privacy default
  input_lock:
    timeout_seconds: 5
```

## Running Tests

```bash
pytest
```

## Development Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| **Phase 0** | Foundation and system architecture | Complete |
| **Phase 1** | Voice system (speech-to-text) | Complete |
| **Phase 2** | Computer control foundation | Current |
| Phase 3 | AI brain integration | Planned |
| Phase 4 | Computer vision | Planned |
| Phase 5 | Gesture control | Planned |

## License

MIT License — see [LICENSE](LICENSE).