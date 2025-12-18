# API Documentation

This document provides details on the internal API structure of ShowOnce.

## `showonce.models`

The core data models used throughout the application.

### `Workflow`
Represents a recorded session.
- `steps`: List of `WorkflowStep`.
- `analyzed`: Boolean indicating if AI analysis has run.
- `metadata`: `WorkflowMetadata`.

### `Action`
Represents an inferred automation action.
- `action_type`: `ActionType` enum (CLICK, TYPE, etc.).
- `target`: `ElementTarget` (selectors and coordinates).
- `value`: Optional value for TYPE/SELECT actions.
- `is_variable`: Boolean for parameterized actions.

## `showonce.analyze`

Handles AI-powered interaction inference.

### `ActionInferenceEngine`
- `analyze_workflow(workflow)`: Main entry point for workflow analysis.
- `_parse_to_actions(response)`: Converts Claude JSON to `Action` objects.

## `showonce.generate`

Generates executable scripts.

### `PlaywrightGenerator`
Generates Python Playwright scripts.
- `generate(action_sequence)`: Returns script as string.

### `SeleniumGenerator`
Generates Selenium WebDriver scripts.

### `PyAutoGUIGenerator`
Generates desktop automation scripts.

## `showonce.capture`

Handles screenshot and metadata capture.

### `ScreenCapture`
Cross-platform screenshot utility.

### `HotkeyListener`
Listens for capture and stop hotkeys via `pynput`.
