# ShowOnce Architecture

This document describes the high-level architecture of ShowOnce.

## Overview

ShowOnce is an AI-powered tool that learns automation workflows from screenshots. Users demonstrate a task by capturing screenshots with descriptions, and ShowOnce generates executable automation scripts.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SHOWONCE ARCHITECTURE                              │
└─────────────────────────────────────────────────────────────────────────────┘

  User Demonstration          AI Analysis              Code Generation
  ──────────────────         ────────────             ─────────────────
  
  ┌──────────────┐          ┌──────────────┐          ┌──────────────┐
  │   CAPTURE    │          │   ANALYZE    │          │   GENERATE   │
  │   MODULE     │─────────►│   MODULE     │─────────►│   MODULE     │
  └──────────────┘          └──────────────┘          └──────────────┘
         │                         │                         │
         ▼                         ▼                         ▼
  • Screenshot capture      • Claude Vision API      • Template engine
  • Hotkey listener         • Image comparison       • Playwright/Selenium
  • Metadata collection     • Action inference       • Variable detection
```

## Core Modules

### 1. Capture Module (`showonce/capture/`)

**Responsibility:** Record user demonstrations

**Components:**
- `recorder.py` - Main recording orchestrator
- `hotkeys.py` - Keyboard shortcut handling (pynput)
- `screenshot.py` - Screen capture (mss)
- `metadata.py` - Window/mouse info collection

**Data Flow:**
```
User presses hotkey → Capture screenshot → Collect metadata → Store in Workflow
```

### 2. Analyze Module (`showonce/analyze/`)

**Responsibility:** AI-powered screenshot analysis

**Components:**
- `vision.py` - Claude API integration
- `differ.py` - Screenshot comparison
- `inference.py` - Action inference logic
- `prompts.py` - AI prompt templates

**Data Flow:**
```
Workflow → Screenshot pairs → Claude Vision → Inferred actions → ActionSequence
```

### 3. Generate Module (`showonce/generate/`)

**Responsibility:** Code generation from analyzed workflows

**Components:**
- `generator.py` - Main code generation logic
- `templates/` - Framework-specific templates
- `validators.py` - Generated code validation

**Data Flow:**
```
ActionSequence → Template selection → Code generation → Executable script
```

## Data Models

### Workflow
```python
Workflow
├── name: str
├── description: str
├── steps: List[WorkflowStep]
├── metadata: WorkflowMetadata
└── analysis_results: Optional[Dict]
```

### WorkflowStep
```python
WorkflowStep
├── step_number: int
├── description: str
├── screenshot_path: str
├── screenshot_base64: str
└── metadata: StepMetadata
```

### Action
```python
Action
├── action_type: ActionType (click, type, scroll, etc.)
├── sequence: int
├── target: ElementTarget
├── value: Optional[str]
├── is_variable: bool
└── confidence: float
```

### ElementTarget
```python
ElementTarget
├── description: str
├── selectors: List[Selector]
├── coordinates: Optional[tuple]
└── bounding_box: Optional[dict]
```

## Configuration

Configuration is managed through:
1. Environment variables (`.env` file)
2. `Config` singleton class

Key settings:
- `ANTHROPIC_API_KEY` - Claude API access
- `CAPTURE_HOTKEY` - Screenshot capture trigger
- `DEFAULT_FRAMEWORK` - Playwright/Selenium/PyAutoGUI

## File Storage

```
workflows/
├── my_workflow/
│   ├── workflow.json      # Workflow data
│   └── screenshots/       # Screenshot files
│       ├── step_001.png
│       ├── step_002.png
│       └── ...
└── another_workflow/
    └── ...
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `showonce record` | Start recording a workflow |
| `showonce analyze` | Analyze recorded workflow with AI |
| `showonce generate` | Generate automation script |
| `showonce run` | Execute generated script |
| `showonce list` | List all workflows |
| `showonce info` | Show workflow details |

## Technology Stack

- **Python 3.10+** - Core language
- **Anthropic Claude API** - Vision analysis
- **Playwright** - Browser automation (primary)
- **mss** - Screenshot capture
- **pynput** - Keyboard/mouse events
- **Pydantic** - Data validation
- **Click** - CLI framework
- **Rich** - Terminal output

## Security Considerations

1. **API Keys** - Stored in `.env`, never committed to git
2. **Screenshots** - May contain sensitive data, stored locally
3. **Generated Code** - Should be reviewed before execution
4. **Sandboxing** - Consider Docker for untrusted workflows

## Future Enhancements

- [ ] Web UI with Streamlit
- [ ] Browser extension for easier capture
- [ ] Loop detection in workflows
- [ ] Cloud storage for workflows
- [ ] Team collaboration features
