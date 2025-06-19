from fastmcp import FastMCP
from tools.tool_manager import handle_request
from mcp_server.system_utils import check_and_setup_package_managers
import platform
import argparse

# Initialize MCP Server
mcp = FastMCP("DevEnv MCP Server")

# Global variable to store system setup information
system_setup_info = None

def initialize_system():
    """
    Initialize the system by setting up package managers.
    This runs when the server starts, before any OpenAI requests.
    """
    global system_setup_info
    
    print("Initializing development environment...")
    
    # Check and setup package managers based on OS
    system_setup_info = check_and_setup_package_managers()
    
    print(f"OS detected: {system_setup_info['os_type']}")
    for message in system_setup_info['messages']:
        print(f"  - {message}")
    
    if system_setup_info['setup_success']:
        print(f"Package manager ready: {system_setup_info['package_manager']}")
    else:
        print("Package manager setup incomplete")
    
    print("System initialization complete!")
    return system_setup_info

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

# Server info resource - Enhanced with comprehensive system information
@mcp.resource("info://server")
def server_info() -> dict:
    """
    Returns comprehensive metadata about this MCP server and the user's system.
    OpenAI gets this information immediately when connecting.
    """
    global system_setup_info
    
    # Ensure system is initialized
    if system_setup_info is None:
        system_setup_info = initialize_system()
    
    return {
        "name": "DevEnv MCP Server",
        "version": "2.0",
        "description": "MCP server for software installation and development environment management on Mac and Linux",
        "tool_count": len(mcp.tools),
        
        # Comprehensive system information for OpenAI
        "user_system": {
            "os_type": system_setup_info.get("os_type", "unknown"),
            "os_version": platform.release(),
            "machine_type": platform.machine(),
            
            "package_manager": {
                "name": system_setup_info.get("package_manager"),
                "available": system_setup_info.get("setup_success", False),
                "installation_was_needed": system_setup_info.get("installation_needed", False)
            },
            
            "setup_status": {
                "ready_for_installations": system_setup_info.get("setup_success", False),
                "setup_messages": system_setup_info.get("messages", [])
            }
        },
        
        # Guidance for OpenAI
        "capabilities": [
            "Auto-install Homebrew on Mac if missing",
            "Update package lists on Linux",
            "Install development tools (git, docker, nodejs, python, etc.)",
            "Check tool versions and status",
            "Cross-platform support (Mac and Linux only)"
        ]
    }

# System setup tool - OpenAI can call this to get current system status
@mcp.tool()
def get_system_setup() -> dict:
    """
    Returns the current system setup information including OS and package manager status.
    OpenAI can call this to understand what's available on the user's system.
    Returns:
      Dictionary with OS type, package manager info, and setup status
    """
    global system_setup_info
    
    if system_setup_info is None:
        # If not initialized yet, do it now
        system_setup_info = initialize_system()
    
    return {
        "status": "success",
        "system_info": system_setup_info
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
    
    # Initialize system BEFORE starting the server
    # This ensures package managers are ready when OpenAI first connects
    initialize_system()
    
    print(f"\nStarting HTTP server on {args.host}:{args.port}")
    print("OpenAI models can now send HTTP requests to this server")
    print("System information is ready for immediate LLM queries")
    
    # Use streamable-http transport for cloud LLM integration
    mcp.run(transport="streamable-http", host=args.host, port=args.port, path="/mcp")
        
    print("MCP Server stopped.")

if __name__ == "__main__":
    main()