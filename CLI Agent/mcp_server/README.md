# CLI Agent - MCP Server Component

Model Context Protocol (MCP) server for development tool management. This component provides HTTP-based integration with OpenAI and other cloud LLMs for automated development environment setup.

## Features

- **HTTP Transport**: Uses FastAPI and uvicorn for cloud LLM integration
- **Cross-Platform Support**: Supports Windows (winget), macOS (Homebrew), and Linux (apt/dnf/pacman/apk)
- **System Information**: Provides comprehensive system details to LLMs
- **Tool Management**: Install, update, uninstall, and check development tools
- **Code Generation**: Generate code from natural language descriptions using OpenAI
- **JSON-RPC 2.0**: Compliant protocol for LLM communication
- **Team Architecture**: Clean separation between MCP server and tool implementations

## Quick Start

### Setup

```bash
# Install dependencies
pip install -e .

# Or using uv
uv pip sync requirements.txt
```

### Running the Server

```bash
# Using CLI command
cli-agent server --host localhost --port 8000

# Or direct Python execution
python -m mcp_server.mcp_server --host localhost --port 8000
```

### Server Startup

The server starts a FastAPI application with JSON-RPC 2.0 endpoints:

```
Starting MCP server on localhost:8000...
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://localhost:8000 (Press CTRL+C to quit)
```

## OpenAI Integration

Configure your OpenAI client to connect to the MCP server:

```python
mcp_config = {
    "transport": "http",
    "host": "localhost",
    "port": 8000,
    "path": "/mcp"
}
```

### Available Methods

- **`tool_action_wrapper`**: Unified tool management with parameters:
  - `task`: "install", "uninstall", "update", or "version"
  - `tool_name`: Name of the tool to manage
  - `version`: Version to install/update (optional, defaults to "latest")

- **`generate_code`**: Generate code from description:
  - `description`: Natural language description of the code to generate

- **`info://server`**: Get system information (no parameters required)

## Platform Support

### Windows
- **Package Manager**: winget (Windows Package Manager)
- **Features**: Silent installation, automatic agreement acceptance
- **Special Handling**: Ambiguous package resolution with interactive selection

### macOS
- **Package Manager**: Homebrew (brew)
- **Features**: Formula and cask support
- **Requirements**: Homebrew must be installed manually

### Linux
- **Package Managers**: 
  - Ubuntu/Debian: apt
  - RHEL/CentOS: dnf/yum
  - Arch Linux: pacman
  - Alpine: apk
- **Features**: Automatic package manager detection

## Project Structure

```
├── mcp_server/
│   ├── mcp_server.py      # Main FastAPI server
│   ├── system_utils.py    # System utilities
│   └── __init__.py
├── tools/
│   ├── tool_manager.py    # Integration layer
│   ├── os_utils.py        # OS detection utilities
│   ├── constants.py       # Tool definitions
│   ├── code_generator.py  # Code generation utilities
│   └── installers/        # Platform-specific installers
└── pyproject.toml         # Package configuration
```

## Architecture

- **FastAPI Server**: Handles HTTP requests and JSON-RPC 2.0 protocol
- **Tool Handlers**: Direct subprocess calls to platform package managers
- **Code Generation**: OpenAI GPT-4o integration for code generation
- **Clean Boundaries**: MCP logic separated from tool implementation details

## Testing

Test the server:

```bash
# Start the server
python -m mcp_server.mcp_server --port 8000

# Test with curl
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "info://server",
    "params": {}
  }'

# Test tool installation
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "2",
    "method": "tool_action_wrapper",
    "params": {
      "task": "install",
      "tool_name": "docker",
      "version": "latest"
    }
  }'
```

## Technical Details

**Supported Platforms:**
- Windows (with winget)
- macOS (with Homebrew)
- Linux (Ubuntu/apt, RHEL/yum, Fedora/dnf, Arch/pacman, Alpine/apk)

**Dependencies:**
- Python >=3.8
- fastapi
- uvicorn
- fastmcp >=0.1.0

**Key Features:**
- FastAPI-based HTTP transport for cloud LLM integration
- Cross-platform package manager support
- JSON-RPC 2.0 compliant protocol
- OpenAI GPT-4o code generation
- Ambiguous package resolution for Windows winget
- Production-ready with proper error handling

## Error Handling

The server provides structured error responses:

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "result": {
    "status": "error",
    "message": "No supported package manager found."
  }
}
```

## Development

To extend the server:

1. Add new tool handlers in `mcp_server.py`
2. Update the JSON-RPC endpoint to handle new methods
3. Add platform-specific logic in the tool handlers
4. Test with the CLI agent integration
