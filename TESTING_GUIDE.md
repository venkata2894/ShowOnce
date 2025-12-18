# ShowOnce - Manual Testing Guide

## Pre-requisites Check

Run these commands first to ensure everything is set up:

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate

# Check config is valid
python -m showonce.cli config

# Run automated tests
pytest tests/ -v
```

---

## Test 1: Record a Workflow (Capture Module)

### Step 1.1: Start Recording
```powershell
python -m showonce.cli record --name "test_flow" --description "Testing ShowOnce"
```

### Step 1.2: Perform Actions
1. Open any browser or application
2. Press **Ctrl+Shift+S** to capture screenshot
3. Type a description when prompted (e.g., "Opened browser")
4. Repeat 2-3 times with different actions
5. Press **Ctrl+Shift+Q** to stop recording

### Expected Result:
- Banner shows hotkey information
- Each capture prompts for description
- Workflow saved to `workflows/test_flow/`

---

## Test 2: List Workflows

```powershell
python -m showonce.cli list
```

### Expected Result:
- Table shows workflow name, steps count, analyzed status
- Your `test_flow` should appear

---

## Test 3: View Workflow Info

```powershell
python -m showonce.cli info --workflow test_flow
```

### Expected Result:
- Shows workflow details
- Lists all captured steps

---

## Test 4: Analyze Workflow (AI Analysis)

```powershell
python -m showonce.cli analyze --workflow test_flow
```

### Expected Result:
- Progress bar shows analysis progress
- Each action is displayed with confidence
- Workflow marked as analyzed

---

## Test 5: Generate Playwright Script

```powershell
python -m showonce.cli generate --workflow test_flow --framework playwright
```

### Expected Result:
- Shows code preview (first 30 lines)
- Saves to `generated/test_flow_playwright.py`
- Shows success message

---

## Test 6: Generate Selenium Script

```powershell
python -m showonce.cli generate --workflow test_flow --framework selenium
```

### Expected Result:
- Generates Selenium code
- Saves to `generated/test_flow_selenium.py`

---

## Test 7: Generate PyAutoGUI Script

```powershell
python -m showonce.cli generate --workflow test_flow --framework pyautogui
```

### Expected Result:
- Generates PyAutoGUI code
- Saves to `generated/test_flow_pyautogui.py`

---

## Test 8: View Generated Scripts

```powershell
# View Playwright script
Get-Content generated\test_flow_playwright.py

# View Selenium script
Get-Content generated\test_flow_selenium.py
```

---

## Test 9: Run Generated Script (Optional)

**Note:** This will actually execute the automation!

```powershell
# Validate script first
python -c "from showonce.generate import ScriptRunner; r = ScriptRunner('generated/test_flow_playwright.py'); print('Valid:', r.validate_script())"

# Run the script (if you want to test execution)
python -m showonce.cli run --workflow test_flow --framework playwright
```

---

## Quick Module Import Tests

Run these to verify all modules load correctly:

```powershell
# Test all imports
python -c "
print('Testing imports...')

# Capture module
from showonce.capture import ScreenCapture, HotkeyListener, MetadataCollector, RecordingSession
print('✓ Capture module OK')

# Analyze module
from showonce.analyze import ClaudeVision, ActionInferenceEngine, build_transition_prompt
print('✓ Analyze module OK')

# Generate module
from showonce.generate import PlaywrightGenerator, SeleniumGenerator, PyAutoGUIGenerator
from showonce.generate import get_generator, list_frameworks, ScriptRunner
print('✓ Generate module OK')

# Models
from showonce.models import Workflow, Action, ActionType, ActionSequence
print('✓ Models OK')

print('')
print('All modules loaded successfully!')
"
```

---

## Checklist

| Test | Status |
|------|--------|
| Config check | ☐ |
| Automated tests pass | ☐ |
| Record workflow | ☐ |
| List workflows | ☐ |
| View workflow info | ☐ |
| Analyze workflow | ☐ |
| Generate Playwright | ☐ |
| Generate Selenium | ☐ |
| Generate PyAutoGUI | ☐ |
| Module imports | ☐ |

---

## Troubleshooting

### Issue: Hotkeys not working
```powershell
# Check hotkey configuration
python -m showonce.cli config
```

### Issue: API key not found
```powershell
# Verify .env file
Get-Content .env
```

### Issue: Module import error
```powershell
# Reinstall dependencies
pip install -r requirements.txt
```
