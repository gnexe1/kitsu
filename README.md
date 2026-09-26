# POPAL — Personal AI Computer Agent

POPAL is a cross-platform personal AI computer agent with **Voice + Brain + Vision + Gesture + Hands**.

## What's New in Phase 5

Phase 5 adds **Gesture Control** — hand tracking and gesture recognition via webcam:

- **Camera abstraction** — OpenCV VideoCapture with privacy controls
- **Hand detection** — MediaPipe HandLandmarker (21 landmarks per hand)
- **Gesture recognition** — OPEN_PALM, FIST, POINT, PINCH, THUMBS_UP, THUMBS_DOWN, V_SIGN
- **Confidence filtering** — configurable threshold (default 0.85)
- **Debouncing** — temporal confirmation prevents single-frame false positives
- **Cooldown** — prevents rapid-fire gesture actions
- **Gesture policy** — maps gestures to actions (emergency stop, click, move, confirm)
- **Pointer mapping** — hand position to screen coordinates with smoothing
- **Emergency stop gesture** — OPEN_PALM triggers system-wide stop
- **Confirmation gesture** — THUMBS_UP confirms pending actions
- **Privacy controls** — no frame saving, no upload, no recording
- **Safe test mode** — `gesture test` detects gestures without executing actions
- All gesture events flow through the existing safety pipeline

### Gesture Pipeline

```
Webcam Frame
    |
Hand Detection (MediaPipe)
    |
21 Hand Landmarks
    |
Gesture Classification
    |
Confidence Filter (≥0.85)
    |
Debounce (N consecutive frames)
    |
Cooldown (500ms)
    |
Gesture Policy
    |
Structured Event → Safety Engine → Computer Tools
```

The gesture system **observes** — it never directly executes actions.

## Supported Gestures

| Gesture | Default Action | Description |
|---------|---------------|-------------|
| OPEN_PALM | Emergency Stop | All fingers extended |
| FIST | Ignored | All fingers folded |
| POINT | Pointer Move | Index finger extended |
| PINCH | Mouse Click | Thumb + index tips together |
| THUMBS_UP | Confirm | Thumb extended upward |
| THUMBS_DOWN | Ignored | Thumb extended downward |
| V_SIGN | Ignored | Index + middle extended |

## Architecture

```
Voice → STT → Parser → AI Brain → Vision → Gestures → Safety → Computer → Action
```

### Module Structure

```
src/popal/
├── core/          Command processing, execution, routing, state
├── safety/        Policies, permissions, confirmation
├── tools/         Base tool interface, registry
├── platform/      OS detection, adapters
├── computer/      Mouse, keyboard, screen, window, application
├── voice/         Voice system (push-to-talk, STT, TTS)
├── ai/            AI Brain (reasoning + planning)
├── vision/        Computer Vision (screen understanding)
├── gestures/      Gesture Control (Phase 5)
│   ├── types.py          HandLandmark, Hand, GestureEvent, GestureType
│   ├── errors.py         Gesture-specific errors
│   ├── camera.py         Abstract CameraProvider interface
│   ├── landmarks.py      Abstract LandmarkDetector interface
│   ├── recognizer.py     Gesture classification from landmarks
│   ├── debounce.py       Temporal gesture confirmation
│   ├── cooldown.py       Action cooldown timer
│   ├── policy.py         Gesture-to-action mapping policy
│   ├── mapper.py         GestureEvent to POPAL command mapping
│   ├── pointer.py        Hand position to screen coordinate mapping
│   ├── calibration.py    Camera-to-screen calibration
│   ├── privacy.py        Privacy controls
│   ├── provider.py       Abstract GestureProvider interface
│   ├── service.py        GestureService orchestrating the pipeline
│   └── providers/
│       └── local.py      OpenCV camera + MediaPipe HandLandmarker
├── memory/        SQLite database
├── cli/           Command-line interface
└── utils/         Logging, configuration, errors
```

## Installation

```bash
cd POPAL
pip install -e ".[dev,voice]"
```

Gesture dependencies (mediapipe, opencv) are installed automatically.

### Hand Landmarker Model

The MediaPipe hand landmarker model is downloaded automatically on first use.
If the model file is missing, gesture detection degrades gracefully.

## CLI Commands — Gestures

| Command | Description |
|---------|-------------|
| `gesture status` | Show gesture system status |
| `gesture devices` | List available cameras |
| `gesture test` | Safe test mode (no computer actions) |
| `gesture mappings` | Show gesture-to-action mappings |
| `gesture privacy` | Show privacy settings |
| `gesture stop` | Stop gesture service |

## Safety Model

Gesture-specific safety:
- Gesture events NEVER directly execute computer actions
- Emergency stop gesture (OPEN_PALM) has highest priority
- Confirmation gesture (THUMBS_UP) only works with pending confirmations
- Confidence threshold prevents low-confidence actions
- Debounce prevents accidental repeated triggers
- Cooldown prevents rapid-fire actions
- Camera frames not saved, uploaded, or recorded
- No face recognition or identity tracking

## Configuration

```yaml
gestures:
  enabled: false              # disabled by default (privacy-first)
  camera_index: 0
  min_confidence: 0.85
  confirmation_frames: 3
  cooldown_ms: 500
  save_frames: false
  allow_external_processing: false
  pointer:
    enabled: false
    smoothing: 0.5
    deadzone: 0.02
  mappings:
    OPEN_PALM: emergency_stop
    PINCH: mouse_click
    POINT: pointer_move
    THUMBS_UP: confirm
```

## Development Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| **Phase 0** | Foundation and system architecture | Complete |
| **Phase 1** | Voice system (speech-to-text) | Complete |
| **Phase 2** | Computer control foundation | Complete |
| **Phase 3** | AI Brain (reasoning + planning) | Complete |
| **Phase 4** | Computer vision | Complete |
| **Phase 5** | Gesture control | Current |
| Phase 6 | Advanced application control | Planned |

## License

MIT License — see [LICENSE](LICENSE).