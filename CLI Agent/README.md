# DevForge CLI Agent

An AI-powered development assistant with MCP (Model Context Protocol) integration that lets you manage dev tools, environments, SSH/Git, VS Code extensions, and generate code using natural language. Fully supports Windows, macOS, and Linux (Debian/Ubuntu based) with platform‑aware install logic.

## Features

- **Natural Language Commands**: Use plain English to install, uninstall, update, and check versions of development tools
- **MCP Integration**: Built-in MCP server and client for enhanced tool management capabilities
- **Cross-Platform Support**: Works on Windows, macOS, and Linux
- **Code Generation**: Generate Python code from natural language descriptions
- **System Information**: Get detailed system and server information
- **Enhanced macOS App Detection**: Improved version checking for GUI applications
- **Environment Management**: Check/set/remove env vars, list variables
- **Port & Service Checks**: Query if a TCP port is free or a service is running
- **VS Code Extension Management**: Install / uninstall VS Code extensions (with macOS/Linux fallback download)
- **Git Automation**: Generate / view SSH keys, add key to GitHub (PAT), clone repos, check SSH auth
- **Interactive Ambiguous Installs**: Choose between multiple winget package matches during install
- **Auto Server Startup**: CLI auto-spawns MCP server if not already running
- **Live Server Logs**: Stream or view recent MCP server logs via CLI

## Prerequisites

- **Python 3.8+** (3.11 recommended)
- **Git** (for cloning / SSH ops)
- **OpenAI API Key** (required for parsing + code generation)
- **VS Code** (optional, for extension management)

### OS-Specific Base Setup

#### macOS
```bash
# Homebrew (if missing)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Core tools
brew install python git

# Recommended fast package manager for this project
brew install uv
```

#### Linux (Debian / Ubuntu)
```bash
sudo apt update
sudo apt install -y python3 python3-pip git curl zip unzip ca-certificates
# (Optional) Install uv (faster env + resolver)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Windows
1. Install Python (ensure “Add python.exe to PATH” is checked) → https://python.org/downloads/
2. Install Git → https://git-scm.com/download/win
3. (Optional) Install winget (ships with modern Windows 11 / updated 10) – required for installs
4. (Optional) VS Code → https://code.visualstudio.com/

Check winget:
```powershell
winget --version
```
If missing, update Windows or install App Installer from Microsoft Store.

## Quick Setup

### 1. Clone
```bash
git clone <repository-url>
cd "DevForge CLI Agent"
```

### 2. Install (Choose per OS)

#### macOS (uv recommended)
```bash
uv sync
uv pip install -e .
# (Optional) activate venv for shorter commands
source .venv/bin/activate
```

#### Linux (Debian/Ubuntu)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt -e .
# OR if uv installed
uv pip install -e .
```

#### Windows (PowerShell)
```powershell
git clone <repository-url>
cd "DevForge CLI Agent"
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt -e .
```

### 3. Set API Key
```bash
# bash / zsh / Linux / macOS
export OPENAI_API_KEY="your-api-key-here"
```
```powershell
$env:OPENAI_API_KEY = "your-api-key-here"
```
Persist it (optional): add to ~/.zshrc, ~/.bashrc, or PowerShell profile `$PROFILE`.

### 4. Run Commands

#### macOS
Option A (activated venv):
```bash
cli-agent run "system info"
cli-agent run "install slack"
cli-agent run "audacity version"
cli-agent run "generate code for a hello world flask app"
```
Option B (no activation, using uv):
```bash
uv run cli-agent run "system info"
uv run cli-agent run "install slack"
uv run cli-agent run "audacity version"
uv run cli-agent run "generate code for a hello world flask app"
```

#### Linux (Ubuntu/Debian)
```bash
cli-agent run "system info"
cli-agent run "install docker"
cli-agent run "openjdk 17 version"
cli-agent run "generate code for a fastapi hello world"
```

#### Windows (PowerShell)
```powershell
cli-agent run "system info"
cli-agent run "install node"
cli-agent run "python version"
cli-agent run "generate code for a flask api"
```

### 5. (Optional) View Live Server Logs
```bash
# Last 100 lines
cli-agent logs -n 100
# Follow (tail -f)
cli-agent logs --follow
# Using uv
uv run cli-agent logs --follow
```

> **Note**: Activate the virtual environment for many sequential commands; use `uv run` (mac/Linux) or just the global script when you prefer one-offs. Windows installs an entry point script into the venv / Scripts folder.

## Usage

### Basic Commands

```bash
# Install tools (OS aware)
cli-agent run "install slack"
cli-agent run "get nodejs"
cli-agent run "setup python"

# Check versions
cli-agent run "audacity version"
cli-agent run "python version"
cli-agent run "what version is nodejs"

# Update tools
cli-agent run "update slack"
cli-agent run "upgrade nodejs"

# Uninstall tools
cli-agent run "remove slack"
cli-agent run "uninstall nodejs"

# Generate code
cli-agent run "generate a python function to sort a list" --output sort.py
cli-agent run "create a flask web server"

# System information
cli-agent run "system info"
cli-agent run "what os am i using"

# Git & SSH
cli-agent run "generate ssh key with email dev@example.com"
cli-agent run "show my ssh key"
cli-agent run "check ssh auth"
cli-agent run "clone repo git@github.com:owner/repo.git to projects"
cli-agent run "add my ssh key to github"  # supply PAT via env (GITHUB_PAT) or prompt soon (see Git section)

# VS Code extensions
cli-agent run "install vscode extension ms-python.python"
cli-agent run "remove vscode extension ms-python.python"

# System configuration
cli-agent run "check env JAVA_HOME"
cli-agent run "set env FOO=bar"
cli-agent run "list env vars"
cli-agent run "is port 8000 open"
cli-agent run "check service running on 8000"
cli-agent run "is service slack running"
```

### Command Options

```bash
# Save generated code to file
cli-agent run "generate code" --output filename.py

# Enable verbose output
cli-agent run "install slack" --verbose

# Server options
cli-agent server --host localhost --port 8000 --verbose
```

### Git Automation Tasks (Natural Language Examples)
All git/SSH actions route through a unified `git_setup` task (auto-detects existing keys, avoids overwrites, supports GitHub upload via PAT).

```bash
# Generate a new SSH key (id_rsa) if it does not exist
cli-agent run "generate ssh key for dev@example.com"

# Show existing public key
cli-agent run "show my ssh key"

# Attempt adding key to GitHub automatically (requires PAT in env GITHUB_PAT or phrase includes token soon)
cli-agent run "add my ssh key to github"

# Clone repository (SSH URL recommended)
cli-agent run "clone repo git@github.com:owner/repo.git"

# Check SSH connectivity to GitHub
cli-agent run "check ssh auth"
```

Supported git actions (internal): `generate_ssh_key`, `get_public_key`, `check_ssh`, `clone`, `add_ssh_key`.

### VS Code Extension Management
```bash
cli-agent run "install vscode extension ms-python.python"
cli-agent run "uninstall vscode extension ms-python.python"
```
On macOS/Linux if standard install fails (network / marketplace restrictions), a fallback download + local VSIX install is attempted (mac uses platform-specific module). Windows does not use the fallback path.

### System / Environment Management
`system_config` task powers these natural language phrases (cross‑platform; service detection varies by OS — Linux uses systemctl / processes, macOS uses ps & app bundles, Windows uses service / tasklist heuristics):

Actions: `check`, `set`, `remove_env`, `list_env`, `is_port_open`, `is_service_running`.

Examples:
```bash
cli-agent run "check env JAVA_HOME"
cli-agent run "set env MY_TOKEN=12345"
cli-agent run "remove env MY_TOKEN"
cli-agent run "list env vars"
cli-agent run "is port 5432 open"
cli-agent run "is service docker running"
```

Return formatting:
- Success variable check: `✓ VAR = value`
- Port free/in use messages

### Ambiguous Install Resolution
When multiple Windows winget packages match (e.g., "python"), you get an interactive numbered selection. On macOS the resolver maps names (e.g., openjdk 17 → openjdk@17). On Linux the resolver chooses among apt/snap/SDKMAN with fallbacks.

### Auto-Starting the MCP Server
Any `cli-agent run` or `cli-agent logs` invocation ensures the MCP server is running (auto-spawn). Manual start rarely needed.

### Viewing Server Logs
```bash
cli-agent logs -n 200
cli-agent logs --follow
```
Rich-rendered table includes timestamp, level, and message. Follow mode polls periodically.

## Architecture

### Clean Project Structure
```
CLI Agent/
├── cli_agent/          # Main CLI application
│   ├── __init__.py    # Package initialization  
│   └── main.py        # CLI entry point with Typer
│   └── (auto server start / log viewer / interactive ambiguous install selection)
├── mcp_client/        # MCP client implementation
│   ├── __init__.py   # Package exports
│   └── client.py     # HTTP-based MCP client
├── mcp_server/       # MCP server implementation
│   ├── __init__.py  # Package initialization
│   └── mcp_server.py # FastAPI MCP server with logging
├── llm_parser/      # Natural language parsing
│   ├── __init__.py # Package exports
│   └── parser.py   # OpenAI-powered command parser
├── tools/          # Utility tools
│   ├── __init__.py # Package exports
│   └── code_generator.py # Code generation utilities
├── pyproject.toml  # Python project configuration
├── requirements.txt # Dependencies
├── uv.lock        # Dependency lock file
└── README.md      # This file
```

### Core Components

1. **CLI Interface** (`cli_agent/main.py`): 
   - Typer-based CLI with Rich formatting
   - Handles user commands and output formatting

2. **HTTP MCP Client** (`mcp_client/client.py`):
   - Clean HTTP client for MCP communication
   - Simplified interface for tool actions

3. **MCP Server** (`mcp_server/mcp_server.py`):
   - FastAPI-based server with request logging
   - Enhanced macOS application detection
   - Cross-platform tool management
   - JSON-RPC-like endpoint `/mcp/` with tasks: install, uninstall, update, version, system_config, git_setup, install_vscode_extension, uninstall_vscode_extension, generate_code
   - In-memory circular log buffer (last 1000 entries)

4. **LLM Parser** (`llm_parser/parser.py`):
   - OpenAI GPT-4 powered natural language parsing
   - Converts human commands to structured requests
   - Resolves ambiguous tool names and versions per OS (e.g., java 17 -> openjdk-17-jdk on Linux)
   - Supports multi-action JSON arrays for chained operations

5. **Code Generator** (`tools/code_generator.py`):
   - AI-powered code generation utilities
   - Integrated with main CLI workflow
   - Output can be piped to file via `--output`

6. **System Config Layer** (`tools/system_config/*`):
   - Environment variable get/set/remove
   - Service status (platform aware)
   - Port availability checks
   - Bulk environment listing

7. **Git Configurator** (`tools/git_configurator/*`):
   - SSH key generation & retrieval
   - GitHub key upload (API via PAT) or manual guidance
   - Repository cloning (SSH)
   - SSH authentication verification

8. **VS Code Extension Manager** (`tools/installers/vscode_extension*.py`):
   - Install/uninstall extensions
   - macOS/Linux fallback VSIX download if marketplace call fails

9. **Name Resolver** (`tools/utils/name_resolver.py`):
   - Maps user-friendly names to platform-specific packages/executables
   - Handles version-specific transforms (openjdk-17-jdk -> openjdk@17 on mac, etc.)

10. **Version Checkers** (`tools/version_checkers/*`):
    - Multi-strategy detection (CLI flags, registry, file version, path probing)
    - Normalized success messages with source attribution

## Development

### Running from Source
```bash
# Start server in development mode
python -m mcp_server.mcp_server --host localhost --port 8000

# Run CLI agent
python -m cli_agent.main run "your command"
```

### Testing
```bash
# Test server is running
curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": "1", "method": "info://server", "params": {}}'

# Test CLI commands
cli-agent run "system info"
cli-agent run "python version"
cli-agent run "install vscode extension ms-python.python"
cli-agent run "generate ssh key for dev@example.com"
cli-agent run "show my ssh key"
cli-agent run "check ssh auth"
cli-agent run "is port 8000 open"
```

## Troubleshooting

### Common Issues

**1. "Cannot connect to MCP server"**
```bash
# Solution: Start the server first
cli-agent server
```

**2. "OpenAI API key not set"**
```bash
# Solution: Set your API key
export OPENAI_API_KEY="your-key-here"
```

**3. "Command not found: cli-agent"**
```bash
# Solution: Install the package
pip install -e .
# Or use direct Python execution
python -m cli_agent.main run "your command"
```

**4. Import errors**
```bash
# Solution: Install dependencies for mac
uv sync & uv pip install -e .
# Or
pip install -r requirements.txt
```

### Debug Mode
```bash
# Enable verbose logging
cli-agent run "your command" --verbose
```

### Check Installation
```bash
# Verify server is working
cli-agent run "system info"

# Check if tools are detected
cli-agent run "python version"
cli-agent run "audacity version"  # Tests macOS app detection
cli-agent run "show my ssh key"   # Tests git/ssh integration
cli-agent run "install vscode extension ms-python.python" # Tests VS Code extension flow
```

## Configuration

### Environment Variables
- `OPENAI_API_KEY`: Required for natural language parsing & code generation
- `GITHUB_PAT`: (Optional) GitHub Personal Access Token to auto-upload SSH public key

### Server Configuration
The MCP server runs on `localhost:8000` by default and includes:
- Request/response logging
- Enhanced macOS application detection  
- Cross-platform tool management
- JSON-RPC 2.0 protocol support
- In-memory log buffer exposed via `cli-agent logs`
- Git + system configuration task routing

## Security & Tokens
- `OPENAI_API_KEY` needed or parsing/code-gen will fail early.
- `GITHUB_PAT` only used if uploading SSH key; never stored server-side.

## Tips & Best Practices
- Use natural phrasing; synonyms & variants handled (install/add/get me/remove).
- Linux resolver auto-selects apt, snap, or SDKMAN with graceful fallbacks.
- macOS uses Homebrew plus version pin logic (tool@version when supported).
- Windows leverages winget; ambiguous results trigger interactive selection.
- Prefer SSH URLs after generating keys; set GITHUB_PAT for auto upload.
- Use `--output file.py` to save generated code directly.
- Run `cli-agent logs` if behavior seems off.

## Roadmap (Ideas)
- Batch multi-tool environment setup templates
- Automatic rollback on failed multi-step installs
- Parallel install execution
- Extra package managers (Chocolatey, Scoop, pacman, yum)
- Local model parsing fallback

---
Happy building! If something feels missing, run `cli-agent logs` to inspect what's happening under the hood.






