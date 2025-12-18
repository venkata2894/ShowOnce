# CLI Reference

## `record`
Start a new recording session.
```bash
python -m showonce.cli record --name <name> [--description <desc>]
```
- `--name`: Unique name for the workflow.
- `--description`: Optional summary.

## `list`
List all workflows.
```bash
python -m showonce.cli list
```

## `analyze`
Run AI analysis.
```bash
python -m showonce.cli analyze --workflow <name>
```

## `generate`
Generate automation code.
```bash
python -m showonce.cli generate --workflow <name> [--framework <framework>] [--headless]
```
- `--framework`: `playwright` (default), `selenium`, or `pyautogui`.

## `run`
Execute a generated script.
```bash
python -m showonce.cli run --workflow <name> [--params <json>]
```
- `--params`: JSON string for variable parameters.
