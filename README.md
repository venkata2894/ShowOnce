# ShowOnce 🎯

[![Tests](https://github.com/venkata2894/ShowOnce/actions/workflows/test.yml/badge.svg)](https://github.com/venkata2894/ShowOnce/actions)
[![PyPI version](https://img.shields.io/pypi/v/showonce.svg)](https://pypi.org/project/showonce/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

**Show me once. I'll do it forever.**

ShowOnce is an AI-powered automation tool that learns workflows by watching you perform them. It captures your interactions via screenshots, analyzes the transitions using Claude Vision, and generates executable automation scripts in Playwright, Selenium, or PyAutoGUI.

## 🚀 Features

- **Visual Recording**: Capture workflows naturally using hotkeys.
- **AI Analysis**: Uses Claude 3.5 Sonnet Vision to infer actions, selectors, and variables.
- **Multi-Framework Generation**: Generate code for Playwright (Python), Selenium, or PyAutoGUI.
- **Smart Selectors**: Automatically identifies the most robust CSS, XPath, and Text selectors.
- **Web Interface**: Manage, analyze, and generate scripts through a beautiful Streamlit dashboard.
- **Direct Execution**: Run your generated automation directly from the browser with real-time logs and dynamic parameter forms.
- **CLI Power**: Fully functional command-line interface for power users.

## 🛠️ Installation

### 1. Clone the repository
```bash
git clone https://github.com/venkata2894/ShowOnce.git
cd ShowOnce
```

### 2. Set up environment
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\Activate
pip install -r requirements.txt
```

### 3. Configure API Key
Create a `.env` file in the root directory:
```env
ANTHROPIC_API_KEY=your_sk_ant_key_here
```

## 🎯 Quick Start

### Methodology 1: The UI Way (Recommended)
1. Start the dashboard:
   ```bash
   streamlit run showonce/ui/app.py
   ```
2. Create a new workflow and upload your screenshots, or use the CLI to record.

### Methodology 2: The CLI Way
1. **Record**: Capture a new flow
   ```bash
   python -m showonce.cli record --name my_login
   ```
    - Press `Ctrl+Shift+M` to capture a step.
    - Press `Ctrl+Shift+Q` to stop.

2. **Analyze**: Let AI figure out the steps
   ```bash
   python -m showonce.cli analyze --workflow my_login
   ```

3. **Generate**: Create your script
   ```bash
   python -m showonce.cli generate --workflow my_login --framework playwright
   ```

## 📖 CLI Reference

| Command | Description |
|---------|-------------|
| `record` | Start a new recording session |
| `list` | List all recorded workflows |
| `info` | View details of a specific workflow |
| `analyze`| Run AI analysis on a workflow |
| `generate`| Generate automation code |
| `run` | Execute a generated script |
| `config` | View current configuration |

## ⚙️ Configuration

Settings can be managed via `.env` or `showonce/config.py`.

- `ANTHROPIC_API_KEY`: Required for analysis.
- `CAPTURE_HOTKEY`: Default `ctrl+shift+m`.
- `STOP_HOTKEY`: Default `ctrl+shift+q`.
- `DEFAULT_FRAMEWORK`: `playwright`, `selenium`, or `pyautogui`.

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

This project is licensed under the MIT License.
