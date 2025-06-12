# mcp_server.py

from fastmcp import FastMCP
from tools.install import install_tool
import platform

# Initialize MCP Server
mcp = FastMCP("DevEnv MCP Server")

# Software Installation / Version Management Tool
@mcp.tool()
def install_tool_wrapper(tool_name: str, version: str = "latest") -> str:
    """
    Install, update, or check version of a software package.
    Arguments:
      tool_name: name of the tool to install (e.g., "docker", "nodejs")
      version: version string or 'latest' to get the newest version
    Returns:
      Status message about the installation/update/version check
    """
    try:
        return install_tool(tool_name, version)
    except Exception as e:
        raise RuntimeError(f"install_tool failed: {e}")

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
    # Start the MCP server
    print("Starting DevEnv MCP Server...")
    mcp.run(transport="stdio")