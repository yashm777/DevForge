"""
Mac Tool Uninstaller

This file provides a clean interface for uninstalling tools on Mac.
It uses the comprehensive MacToolManager for all uninstall logic.
"""

import logging
from tools.utils.mac_tool_manager import get_manager
from tools.utils.name_resolver import resolve_tool_name

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def uninstall_mac_tool(tool_name):
    """
    Remove a development tool from Mac using the enhanced manager.
    
    Args:
        tool_name: The name of the tool to remove (like "docker", "cursor", etc.)
    
    Returns:
        Dictionary with status, message, and details
    """
    logger.info(f"Starting Mac uninstall: {tool_name}")
    
    try:
        # Resolve tool name for Mac system (handles Linux package names)
        resolved = resolve_tool_name(tool_name, "darwin", "latest", "install")
        resolved_tool_name = resolved["name"]
        logger.info(f"Resolved '{tool_name}' to '{resolved_tool_name}' for Mac uninstall")
        
        # Use the comprehensive tool manager for uninstallation
        manager = get_manager()
        result = manager.uninstall_tool(resolved_tool_name, cleanup=True)
        
        return result
        
    except Exception as e:
        logger.error(f"Uninstall failed for {tool_name}: {e}")
        return {
            "status": "error",
            "message": f"Uninstall failed: {str(e)}",
            "details": {"tool_name": tool_name, "error": str(e)}
        }

# Legacy function aliases for backwards compatibility
def uninstall_tool_mac(tool_name):
    """Legacy function name - use uninstall_mac_tool instead."""
    return uninstall_mac_tool(tool_name)
