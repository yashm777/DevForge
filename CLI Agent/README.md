# DevForge CLI Agent

An AI-powered development assistant with MCP (Model Context Protocol) integration that allows you to manage development tools and environments using natural language commands.

## 🚀 Features

- **Natural Language Commands**: Use plain English to install, uninstall, update, and check versions of development tools
- **MCP Integration**: Built-in MCP server and client for enhanced tool management capabilities
- **Cross-Platform Support**: Works on Windows, macOS, and Linux
- **Code Generation**: Generate Python code from natural language descriptions
- **System Information**: Get detailed system and server information
- **Enhanced macOS App Detection**: Improved version checking for GUI applications

## 📋 Prerequisites

- **Python 3.8+** 
- **Git** (optional, for cloning)
- **OpenAI API Key** (for natural language parsing)

### Quick Prerequisites Check

#### macOS
```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python and Git
brew install python git
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install python3 python3-pip git
```

#### Windows
1. Download Python from [python.org](https://python.org/downloads/)
2. Download Git from [git-scm.com](https://git-scm.com/download/win)

## ⚡ Quick Setup

### 1. Clone & Install
```bash
# Clone the repository
git clone <repository-url>
cd "DevForge CLI Agent"

# Install with UV (recommended)
pip install uv
uv sync && uv pip install -e .

# Or install with pip
pip install -r requirements.txt
```

### 2. Set API Key
```bash or cmd
export OPENAI_API_KEY="your-api-key-here"
```
``` powershell
$env:OPENAI_API_KEY = "API_KEY"
```

### 3. Start the MCP Server
```bash
# Option 1: Using CLI agent
cli-agent server

# Option 2: Direct Python module
python -m mcp_server.mcp_server
```

### 4. Use the Agent
```bash
# Try some commands
cli-agent run "install docker"
cli-agent run "audacity version"
cli-agent run "generate code for a hello world flask app"
```

## 🎯 Usage

### Basic Commands

```bash
# Install tools
cli-agent run "install docker"
cli-agent run "get nodejs" 
cli-agent run "setup python"

# Check versions
cli-agent run "audacity version"
cli-agent run "python version"
cli-agent run "what version is nodejs"

# Update tools
cli-agent run "update docker"
cli-agent run "upgrade nodejs"

# Uninstall tools
cli-agent run "remove docker"
cli-agent run "uninstall nodejs"

# Generate code
cli-agent run "generate a python function to sort a list" --output sort.py
cli-agent run "create a flask web server"

# System information
cli-agent run "system info"
cli-agent run "what os am i using"
```

### Command Options

```bash
# Save generated code to file
cli-agent run "generate code" --output filename.py

# Enable verbose output
cli-agent run "install docker" --verbose

# Server options
cli-agent server --host localhost --port 8000 --verbose
```

## 🏗️ Architecture

### Clean Project Structure
```
CLI Agent/
├── cli_agent/          # Main CLI application
│   ├── __init__.py    # Package initialization  
│   └── main.py        # CLI entry point with Typer
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

4. **LLM Parser** (`llm_parser/parser.py`):
   - OpenAI GPT-4 powered natural language parsing
   - Converts human commands to structured requests

5. **Code Generator** (`tools/code_generator.py`):
   - AI-powered code generation utilities
   - Integrated with main CLI workflow

## 🔧 Development

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
```

## 🐛 Troubleshooting

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
# Solution: Install dependencies
uv sync
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
```

## 📝 Configuration

### Environment Variables
- `OPENAI_API_KEY`: Required for natural language parsing

### Server Configuration
The MCP server runs on `localhost:8000` by default and includes:
- Request/response logging
- Enhanced macOS application detection  
- Cross-platform tool management
- JSON-RPC 2.0 protocol support




