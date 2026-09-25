# POPAL — Personal AI Computer Agent

POPAL is a cross-platform personal AI computer agent with **Brain + Eyes + Hands**.

## What's New in Phase 4

Phase 4 adds **Computer Vision** — screen understanding, OCR, target detection, and visual analysis:

- **Screenshot capture** — reuses Phase 2 screen controller (mss)
- **OCR** — Tesseract-based text recognition with bounding boxes (graceful degradation)
- **Target detection** — text, color, and UI element localization via OpenCV
- **Target matching** — confidence filtering, ambiguity handling, screen bounds validation
- **Visual verification** — before/after screenshot comparison
- **Screen description** — analysis-based description of visible content
- **Privacy controls** — screenshots in memory only, no auto-save/upload, sensitive data redaction
- **Vision service** — orchestrated capture → analyze → return pipeline (never clicks directly)
- **AI integration** — AI Brain recognizes "find Settings", "what's on screen" commands
- All vision observations flow through the existing safety pipeline before any action

### Vision Pipeline

```
User Request ("Find Settings button")
    |
AI Brain → vision_find target=Settings
    |
Vision Service
    |
Capture Screen (in memory)
    |
Privacy Check → OCR + Color + Shape Detection
    |
Target Matching → Confidence Filtering
    |
Vision Result (observations only)
    |
Safety Engine → Computer Tools → Action → Verification
```

The vision system **observes** — it never directly clicks or types.

## Architecture

```
Voice → STT → Parser → AI Brain → Vision → Observations → Safety → Computer → Action
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
├── vision/        Computer Vision (Phase 4)
│   ├── types.py          VisionPoint, VisionRegion, OCRResult, VisionTarget, VisionResult
│   ├── errors.py         Vision-specific errors
│   ├── capture.py        Screenshot acquisition (reuses Phase 2)
│   ├── ocr.py            OCR abstraction + Tesseract provider
│   ├── detector.py       Contour, color, and template detection (OpenCV)
│   ├── locator.py        Text, color, and UI element target finding
│   ├── matcher.py        Confidence filtering and ambiguity resolution
│   ├── analyzer.py       Screen description via image analysis
│   ├── verifier.py       Before/after visual change verification
│   ├── privacy.py        Privacy controls and sensitive data redaction
│   ├── provider.py       Abstract VisionProvider interface
│   ├── service.py        VisionService orchestrating the pipeline
│   └── providers/
│       └── local.py      LocalVisionProvider (OpenCV + optional Tesseract)
├── gestures/      Hand/gesture control (placeholder)
├── memory/        SQLite database
├── cli/           Command-line interface
└── utils/         Logging, configuration, errors
```

## Installation

```bash
cd POPAL
pip install -e ".[dev,voice]"
```

Vision dependencies (opencv-python-headless) are installed automatically.

### Optional: Tesseract OCR

For text recognition, install the Tesseract binary:

```bash
sudo apt install tesseract-ocr
```

The vision system works without Tesseract — OCR degrades gracefully.

## CLI Commands — Vision

| Command | Description |
|---------|-------------|
| `vision status` | Show vision system status |
| `vision screenshot` | Capture screenshot (in memory, not saved) |
| `vision ocr` | Read visible text on screen |
| `vision describe` | Describe what's on screen |
| `vision find "Settings"` | Find a target by text, color, or type |

## Safety Model

Vision-specific safety:
- Screenshots stay in memory by default (never saved/uploaded)
- OCR content treated as untrusted (prompt injection protection)
- Vision-generated coordinates validated against screen bounds
- Confidence thresholds prevent low-confidence actions
- Ambiguity handling asks user instead of guessing
- Vision system has NO click/keyboard methods — observations only

## Configuration

```yaml
vision:
  enabled: false              # disabled by default (privacy-first)
  min_confidence: 0.85
  max_candidates: 5
  save_screenshots: false
  allow_external_processing: false
```

## Development Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| **Phase 0** | Foundation and system architecture | Complete |
| **Phase 1** | Voice system (speech-to-text) | Complete |
| **Phase 2** | Computer control foundation | Complete |
| **Phase 3** | AI Brain (reasoning + planning) | Complete |
| **Phase 4** | Computer vision | Current |
| Phase 5 | Gesture control | Planned |

## License

MIT License — see [LICENSE](LICENSE).