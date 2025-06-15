from fastmcp import FastMCP
from tools.tool_manager import handle_request
import platform

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
        "tool_count": len(mcp.tools),
        "description": "MCP server for software installation and version management",
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version()
        }
    }

if __name__ == "__main__":
    print("Starting DevEnv MCP Server...")
    mcp.run(transport="stdio")
    print("MCP Server is running. Use Ctrl+C to stop.")
# This code sets up a FastMCP server that provides a tool management interface.