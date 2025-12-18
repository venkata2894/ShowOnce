# 🎯 ShowOnce

**"Show me once. I'll do it forever."**

ShowOnce is an AI-powered tool that learns automation workflows from screenshots. Simply demonstrate a task by capturing screenshots, and ShowOnce generates executable automation scripts.

---

## ✨ Features

- 📸 **Visual Recording** — Capture workflows with screenshots and descriptions
- 🧠 **AI Analysis** — Claude Vision understands what actions you performed
- ⚡ **Code Generation** — Automatically generates Playwright/Selenium scripts
- 🔄 **Replay Anywhere** — Run generated automations with custom parameters

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/showonce.git
cd showonce

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### Usage

```bash
# Step 1: Record a workflow
showonce record --name "login_demo"
# Press Ctrl+Shift+S to capture each step
# Press Ctrl+Shift+Q to stop recording

# Step 2: Analyze and generate automation
showonce generate --workflow "login_demo"

# Step 3: Run the automation
showonce run --workflow "login_demo" --params '{"username": "test"}'
```

---

## 📁 Project Structure

```
showonce/
├── showonce/              # Main source code
│   ├── models/            # Data structures
│   ├── capture/           # Screenshot recording
│   ├── analyze/           # AI analysis with Claude
│   ├── generate/          # Code generation
│   └── utils/             # Helper functions
├── workflows/             # Saved workflows
├── tests/                 # Test files
└── docs/                  # Documentation
```

---

## 🔧 How It Works

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   CAPTURE    │     │   ANALYZE    │     │   GENERATE   │     │    RUN       │
│              │────►│              │────►│              │────►│              │
│ Screenshots  │     │ Claude AI    │     │  Playwright  │     │  Execute     │
│ + Descriptions│    │  Vision      │     │   Script     │     │  Automation  │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

1. **Capture**: Record your workflow by taking screenshots and adding descriptions
2. **Analyze**: AI analyzes screenshot transitions to infer actions
3. **Generate**: Produces executable automation code
4. **Run**: Execute the automation with your parameters

---

## 🛠️ Tech Stack

- **Python 3.10+**
- **Anthropic Claude API** — Vision analysis
- **Playwright** — Browser automation
- **Pillow** — Image processing
- **Click** — CLI framework
- **Pydantic** — Data validation

---

## 📖 Documentation

- [Architecture Overview](docs/architecture.md)
- [API Reference](docs/api.md)
- [Contributing Guide](docs/contributing.md)

---

## 🤝 Contributing

Contributions are welcome! Please read our contributing guide before submitting PRs.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

Built with ❤️ using Claude AI by Anthropic.

---

**Made by [Venkata Sai](https://github.com/yourusername)**
