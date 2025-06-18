from fastmcp import FastMCP
from tools.tool_manager import handle_request
import platform
import argparse

# Initialize MCP Server
mcp = FastMCP("DevEnv MCP Server")

# General tool operation wrapper
@mcp.tool()
def tool_action_wrapper(task: str, tool_name: str, version: str = "latest") -> dict:
    """
    Perform an action (install, uninstall, update, version) on a software package.
    Arguments:
      task: operation to perform ('install', 'uninstall', 'update', 'version')
      tool_name: name of the tool (e.g., "docker", "nodejs")
      version: version string or 'latest' (only applicable for install/update)
    Returns:
      Dictionary with status and message
    """
    try:
        request = {
            "task": task,
            "tool": tool_name,
            "version": version
        }
        return handle_request(request)
    except Exception as e:
        return {"status": "error", "message": f"Tool operation failed: {e}"}

# Server info resource
@mcp.resource("info://server")
def server_info() -> dict:
    """
    Returns metadata about this MCP server.
    """
    return {
        "name": "DevEnv MCP Server",
        "version": "2.0",
        "tool_count": len(mcp.tools),
        "description": "MCP server for software installation and development environment management on Mac and Linux",
        "transport": "HTTP for OpenAI cloud integration",
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version()
        }
    }

def main():
    """Entry point for the CLI command and direct execution"""
    # Parse command line arguments for HTTP server configuration
    parser = argparse.ArgumentParser(description="DevEnv MCP Server for OpenAI Cloud Integration")
    parser.add_argument(
        "--host", 
        default="localhost",
        help="Host to bind HTTP server (default: localhost)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8000,
        help="Port to bind HTTP server (default: 8000)"
    )
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("DevEnv MCP Server for OpenAI Cloud Integration")
    print("=" * 50)
    print(f"Starting HTTP server on {args.host}:{args.port}")
    print("OpenAI models can now send HTTP requests to this server")
    
    # Use streamable-http transport for cloud LLM integration
    mcp.run(transport="streamable-http", host=args.host, port=args.port, path="/mcp")
        
    print("MCP Server stopped.")

if __name__ == "__main__":
    main()