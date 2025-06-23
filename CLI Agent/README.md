# DevForge CLI Agent

An AI-powered development assistant with MCP (Model Context Protocol) integration that allows you to manage development tools and environments using natural language commands.

## Features

- **Natural Language Commands**: Use plain English to install, uninstall, update, and check versions of development tools
- **MCP Integration**: Built-in MCP server and client for enhanced tool management capabilities
- **Cross-Platform Support**: Works on Windows, macOS, and Linux
- **Code Generation**: Generate Python code from natural language descriptions
- **System Information**: Get detailed system and server information

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd DevForge-test/CLI\ Agent
```

2. Install dependencies:
```bash
pip install -e .
```

3. Set up your OpenAI API key:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

## Usage

### Basic Commands

The CLI agent supports natural language commands for tool management:

```bash
# Install tools
cli-agent run "install docker"
cli-agent run "get nodejs"
cli-agent run "setup python"

# Uninstall tools
cli-agent run "remove docker"
cli-agent run "uninstall nodejs"

# Update tools
cli-agent run "update docker"
cli-agent run "upgrade python"

# Check versions
cli-agent run "what version of docker"
cli-agent run "check version nodejs"
cli-agent run "python version"

# System information
cli-agent run "system info"
cli-agent run "what os am i using"

# Code generation
cli-agent run "generate code for a hello world function"
cli-agent run "write python code for a calculator"
cli-agent run --output my_code.py "create a web scraper"
```

<!-- ### Chained Commands (coming soon)

You can chain multiple commands together:

```bash
cli-agent run "install docker and tell me what version you used"
cli-agent run "setup nodejs then check its version"
``` -->

### MCP Server

Start the MCP server for enhanced functionality:

```bash
cli-agent server --host localhost --port 8000
```

## Architecture

### Core Components

- **CLI Interface** (`cli_agent/main.py`): Main command-line interface using Typer and Rich
- **LLM Parser** (`llm_parser/parser.py`): Natural language command parsing using OpenAI GPT-4o
- **MCP Client** (`mcp_client/client.py`): HTTP-based MCP client for tool communication
- **MCP Server** (`mcp_server/mcp_server.py`): MCP server providing tool management services
- **Tool Manager** (`tools/tool_manager.py`): Central tool management and code generation

### Tool Management System

The tool management system is organized by platform and action type:

```
tools/
├── installers/     # Tool installation logic
│   ├── windows.py
│   ├── mac.py
│   └── linux.py
├── uninstallers/   # Tool removal logic
│   ├── windows.py
│   ├── mac.py
│   └── linux.py
├── upgraders/      # Tool update logic
│   ├── windows.py
│   ├── mac.py
│   └── linux.py
├── version_checkers/ # Version checking logic
│   ├── windows.py
│   ├── mac.py
│   └── linux.py
├── tool_manager.py # Central tool management
├── os_utils.py     # OS detection utilities
└── constants.py    # System constants
```

### Code Generation

The code generation tool is integrated into the tool manager and uses OpenAI's GPT-4o model to generate Python code from natural language descriptions.

## Configuration

### Environment Variables

- `OPENAI_API_KEY`: Required for natural language parsing and code generation

### Dependencies

Key dependencies include:
- `typer`: CLI framework
- `rich`: Terminal formatting and UI
- `openai`: OpenAI API integration
- `requests`: HTTP client for MCP communication

## Development

### Project Structure

```
CLI Agent/
├── cli_agent/           # Main CLI package
│   ├── __init__.py
│   └── main.py         # CLI entry point
├── llm_parser/         # Natural language parsing
│   ├── __init__.py
│   └── parser.py       # Command parsing logic
├── mcp_client/         # MCP client implementation
│   ├── __init__.py
│   └── client.py       # HTTP-based MCP client
├── mcp_server/         # MCP server implementation
│   ├── __init__.py
│   ├── mcp_server.py   # Server implementation
│   └── system_utils.py # System utilities
├── tools/              # Tool management system
│   ├── installers/     # Platform-specific installers
│   ├── uninstallers/   # Platform-specific uninstallers
│   ├── upgraders/      # Platform-specific upgraders
│   ├── version_checkers/ # Platform-specific version checkers
│   ├── tool_manager.py # Central tool management
│   ├── os_utils.py     # OS detection
│   └── constants.py    # Constants
├── pyproject.toml      # Project configuration
├── requirements.txt    # Dependencies
└── README.md          # This file
```

### Adding New Tools

To add support for a new tool:

1. Implement platform-specific handlers in the appropriate directories
2. Add tool patterns to the LLM parser
3. Update the tool manager if needed

### Testing

Test the CLI agent with various commands:

```bash
# Test basic functionality
cli-agent run "system info"

# Test tool installation
cli-agent run "install docker"

# Test code generation
cli-agent run "generate code for a simple calculator"
```

## Troubleshooting

### Common Issues

1. **OpenAI API Key Not Set**: Ensure `OPENAI_API_KEY` environment variable is set
2. **MCP Server Connection Issues**: Check if the server is running on the correct port
3. **Tool Installation Failures**: Verify platform-specific handlers are implemented

### Debug Mode

Enable verbose output for debugging:

```bash
cli-agent run --verbose "your command here"
```
