# CLI Agent - MCP Server Component

Model Context Protocol (MCP) server for development tool management. This component provides HTTP-based integration with OpenAI and other cloud LLMs for automated development environment setup.

## Features

- **HTTP Transport**: Uses streamable-http for cloud LLM integration
- **Auto Package Manager Setup**: Automatically installs Homebrew on Mac and detects/uses apt/yum/dnf on Linux
- **System Information**: Provides comprehensive system details to LLMs
- **Tool Management**: Install, update, uninstall, and check development tools
- **Cross-Platform**: Supports macOS and Linux
- **Team Architecture**: Clean separation between MCP server and tool implementations

## Quick Start

### Setup

```bash
# Install dependencies
uv pip sync requirements.txt

# Install package (optional, for CLI access)
pip install -e .
```

### Running the Server

```bash
# Using CLI command
cli-agent-server --host localhost --port 8000

# Or direct Python execution
python -m mcp_server.mcp_server --host localhost --port 8000
```

### Server Startup

The server automatically:
1. Detects your operating system
2. Sets up package managers (Homebrew on Mac, apt/yum/dnf on Linux)
3. Collects system information
4. Starts HTTP server for LLM requests

Example output:
```
==================================================
DevEnv MCP Server for OpenAI Cloud Integration
==================================================
Initializing development environment...
OS detected: darwin
  - Homebrew is available
Package manager ready: brew
System initialization complete!

Starting HTTP server on localhost:8000
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

### Available Tools
- **install_tool**: Install development tools
- **update_tool**: Update existing tools
- **uninstall_tool**: Remove tools
- **check_tool_version**: Check tool versions
- **get_system_setup**: Get system configuration

## Project Structure

```
├── mcp_server/
│   ├── mcp_server.py      # Main HTTP server
│   ├── system_utils.py    # System setup logic
│   └── __init__.py
├── tools/
│   ├── tool_manager.py    # Integration layer
│   ├── os_utils.py        # OS detection utilities
│   ├── constants.py       # Tool definitions
│   └── installers/        # Platform-specific installers
└── pyproject.toml         # Package configuration
```

## Architecture

- **MCP Server**: Handles system setup and LLM communication
- **Tools Layer**: Provides integration with platform-specific installers
- **Clean Boundaries**: MCP logic separated from tool implementation details

## Testing

Test the server:

```bash
# Start the server
python -m mcp_server.mcp_server --port 8000

# Test with curl
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/list"}'
```

## Technical Details

**Supported Platforms:**
- macOS (with Homebrew auto-installation)
- Linux (Ubuntu/apt, RHEL/yum, Fedora/dnf)

**Dependencies:**
- Python >=3.12
- fastmcp >=0.1.0
- UV for dependency management

**Key Features:**
- HTTP transport for cloud LLM integration
- Automatic system setup and package manager detection
- Clean separation between MCP server and tool implementations
- Production-ready with proper error handling
