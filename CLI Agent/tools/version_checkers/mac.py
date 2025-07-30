"""
Mac Tool Version Checker

This file provides a clean interface for checking tool versions on Mac.
It uses the comprehensive MacToolManager for all version detection logic.
"""

import logging
from tools.utils.mac_tool_manager import get_manager
from tools.utils.name_resolver import resolve_tool_name

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_version_mac_tool(tool_name, version="latest"):
    """
    Check what version of a tool is installed and active.
    
    Args:
        tool_name: The name of the tool to check (like "python", "docker", etc.)
        version: Not used in version checking, kept for API compatibility
    
    Returns:
        Dictionary with status, message, version, and details
    """
    logger.info(f"Starting Mac version check: {tool_name}")
    
    try:
        # Resolve tool name for Mac system (handles Linux package names)
        resolved = resolve_tool_name(tool_name, "darwin", version, "version_check")
        resolved_tool_name = resolved["name"]
        logger.info(f"Resolved '{tool_name}' to '{resolved_tool_name}' for Mac version check")
        
        # Use the comprehensive tool manager for all version checking
        manager = get_manager()
        result = manager.check_version(resolved_tool_name)
        
        if result.get("status") == "success":
            # Format the success response for backward compatibility
            message = f"{tool_name} is installed - version {result['version']}"
            
            return {
                "status": "success",
                "message": message,
                "version": result["version"],
                "display_name": tool_name,  # Original tool name for CLI display
                "resolved_name": resolved_tool_name,  # Actual resolved name used
                "details": {
                    "requested_tool": tool_name,
                    "resolved_tool": resolved_tool_name,
                    "package_type": result.get("package_type", "unknown"),
                    "is_upgradable": result.get("is_upgradable", False),
                    "version_details": result.get("raw_output", f"Version {result['version']}"),
                    "source": result.get("source", "unknown"),
                    "is_system_python": result.get("is_system_python", False),
                    "in_virtualenv": result.get("in_virtualenv", False),
                    "system_python_version": result.get("system_python_version", result["version"])
                }
            }
        else:
            # Tool not found or error
            message = result.get("message", f"{tool_name} is not installed or not found")
            return {
                "status": "error",
                "message": message,
                "details": {"requested_tool": tool_name}
            }
            
    except Exception as e:
        logger.error(f"Version check failed for {tool_name}: {e}")
        return {
            "status": "error",
            "message": f"Version check failed: {str(e)}",
            "details": {"requested_tool": tool_name, "error": str(e)}
        }

# Legacy function aliases for backwards compatibility
def check_version(tool_name, version="latest"):
    """Legacy function name - use check_version_mac_tool instead."""
    return check_version_mac_tool(tool_name, version)

def check_version_tool_mac(tool_name):
    """Legacy function name - use check_version_mac_tool instead."""
    return check_version_mac_tool(tool_name)

def simple_check_version(tool_name: str) -> str | None:
    """
    Simple version check that returns raw output or None.
    Legacy function for backward compatibility.
    """
    try:
        manager = get_manager()
        result = manager.check_active_version(tool_name)
        
        if result.get("found", False):
            return result.get("raw_output", "")
        else:
            return None
            
    except Exception:
        return None

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python mac.py <tool_name>")
        sys.exit(1)

    tool = sys.argv[1]
    result = check_version_mac_tool(tool)
    if result.get("status") == "success":
        print(f"{tool} version: {result['version']}")
    else:
        print(f"Could not determine version of {tool}: {result.get('message', 'Unknown error')}")
