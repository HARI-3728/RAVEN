# RAVEN - Multi-AI Development Workspace

[![RAVEN Logo](https://via.placeholder.com/150/080A12/168CFF?text=RAVEN)](https://github.com/your-org/raven)

A terminal-based workspace that coordinates 2-5 AI agents to collaborate on a codebase using Textual and Rich.

## 🎯 Purpose

RAVEN provides a single interactive terminal where users can configure multiple AI agents, assign them roles, and watch them collaborate on a codebase in real-time. The application features a complete terminal UI with dynamic screen navigation, agent configuration, and live execution monitoring.

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.11+
- `pip install textual rich pydantic pytest pytest-asyncio pyyaml typer`

### 2. Installation

#### From Source:

```powershell
# Clone the repository
git clone https://github.com/your-org/raven.git
cd raven

# Create a virtual environment
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1

# Install the package in development mode
pip install -e .

# Install test dependencies
pip install -e ".[dev]"
```

### 3. Configure API Keys

Copy the `.env.example` file and add your API keys:

```powershell
cp .env.example .env
```

Edit `.env` with your API keys:

```powershell
notepad .env
```

Add your keys:

```
OPENAI_API_KEY=sk-your-key-here
GEMINI_API_KEY=your-gemini-key-here
ANTHROPIC_API_KEY=your-anthropic-key-here
```

*Note: Local/offline models (Ollama) do not require API keys, but the Ollama CLI must be installed.*

### 4. Initialize a RAVEN Workspace

```powershell
# Initialize a new RAVEN workspace in current directory
raven init

# Or specify a project directory
raven init --project-dir "C:\path\to\project"

# Initialize with 4 agents (default is 2)
raven init --num-agents 4
```

### 5. Start the RAVEN TUI Application

```powershell
raven start
```

Or run the main module directly:

```powershell
python -m raven.main
```

The Textual terminal will launch with:

- **Welcome screen** - RAVEN name, ASCII logo, and theme colors (black #080A12, electric blue #168CFF, purple #842BFF)
- **Project directory selection** - Select or browse your project folder
- **Team size selection** - Choose 2, 3, 4, or 5 agents (dynamic, not hardcoded)
- **Agent configuration** - Configure each agent's provider, model, role, and editable instructions
- **Custom role editor** - Define custom roles for agents
- **Connection test** - Test API connections (demo data labeled clearly)
- **Live workspace** - Agent panels, activity feed, task board, and command input
- **Agent details** - Inspect selected agent's status and output
- **Diff review** - Review changes before applying sensitive operations
- **Settings** - Appearance and behavior preferences

### 6. Keyboard Navigation

| Key | Action |
|-----|--------|
| `q` | Quit application |
| `c` | Configure agents (start configuration flow) |
| `s` | Start agent execution |
| `p` | Pause execution |
| `r` | Resume execution |
| `h` | Toggle help overlay |
| `1-4` | Select 2-5 agents (on Team Size screen) |
| `Enter` | Submit command in live execution |
| `↑/↓` | Navigate interfaces |

## 📋 Screen Navigation Flow

```
Welcome → Project Setup → Team Size → Agent Setup → Connection Test → Live Execution
       ↑           ↑            ↑              ↑              ↑
       ← Back      ← Back       ← Back         ← Back        ← Back
```

## 🛠️ Development

### Running from Source

```powershell
# Set up virtual environment
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1

# Install dependencies
pip install -e ".[dev]"

# Run the TUI
raven start

# Or run main module directly
python -m raven.main
```

### Running Tests

```powershell
# Run all tests
pytest

# Run with coverage
pytest --cov=raven

# Run specific test file
pytest tests/unit/test_config_parser.py
```

### Building

```powershell
# Build the package
pip wheel . --output-dir dist/

# Or install in development mode
pip install -e .
```

## 📦 Configuration Files

RAVEN creates and uses the following configuration files:

- `.env` - API keys (never committed to git)
- `configs/default.yaml` - Default settings
- `configs/providers.yaml` - Provider configurations
- `configs/roles.yaml` - Role definitions
- `configs/team_templates.yaml` - Team templates
- `raven/team_config.yaml` - Per-project agent config
- `raven/.env` - Project-specific environment variables

## 🔒 Security

- API keys are never stored in source code or git
- All credentials come from environment variables
- Dangerous operations require explicit approval
- File paths are validated to prevent traversal
- Git diffs are reviewed before applying sensitive changes

## 📄 License

MIT License - See the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

- Built with [Textual](://textualize.io) for the terminal UI
- Rich terminal rendering and logging
- Typer for CLI commands
- Pydantic for configuration and validation
- Asyncio for asynchronous orchestration
- SQLite for session and task persistence

---

**RAVEN** - Because sometimes you need more than one AI to get the job done.