"""
Mac Tool Installer

This file helps install development tools on Mac computers using Homebrew.
Enhanced with comprehensive tool management features:
- Smart version policy enforcement (tools require explicit versions, apps use latest)
- Proper package classification (tool vs app)
- Shell-aware configuration updates
- System Python detection
"""

import logging
from tools.utils.mac_tool_manager import get_manager
from tools.utils.name_resolver import resolve_tool_name
from tools.upgraders.mac import get_post_upgrade_instructions

# Set up logging so we can see what happens
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def install_mac_tool(tool_name, version="latest"):
    """
    Install a development tool on Mac using Homebrew with enhanced logic.
    
    This is the main function that does all the work.
    
    Args:
        tool_name: The name of the tool the user wants (like "cursor" or "docker")
        version: What version they want (usually "latest")
    
    Returns:
        A dictionary with:
        - status: "success" if it worked, "error" if it didn't
        - message: What happened
        - details: Extra information about what we did
    """
    logger.info(f"Starting Mac install: {tool_name} (version: {version})")
    
    try:
        # Resolve tool name for Mac system (handles Linux package names)
        resolved = resolve_tool_name(tool_name, "darwin", version, "install")
        resolved_tool_name = resolved["name"]
        logger.info(f"Resolved '{tool_name}' to '{resolved_tool_name}' for Mac install")
        
        # Use the comprehensive tool manager for installation
        manager = get_manager()
        
        # Build tool specification
        if version != "latest":
            tool_spec = f"{resolved_tool_name}@{version}"
        else:
            tool_spec = resolved_tool_name
        
        # Install using the enhanced manager
        result = manager.install_tool(tool_spec)
        
        # Enhance successful results with post-installation instructions
        if result.get("status") == "success" and not result.get("already_installed"):
            # Extract version from result or tool specification
            installed_version = result.get("installed_version") or result.get("version")
            if not installed_version and "@" in tool_spec:
                # Extract version from tool specification (e.g., openjdk@17 -> 17)
                installed_version = tool_spec.split("@")[1]
            elif not installed_version:
                installed_version = version
                
            instructions = get_post_upgrade_instructions(resolved_tool_name, installed_version)
            if instructions:
                result["instructions"] = instructions
                result["message"] = f"{result['message']}\n\nNext steps:\n{instructions}"
        
        return result
        
    except Exception as e:
        logger.error(f"Installation failed for {tool_name}: {e}")
        return {
            "status": "error",
            "message": f"Installation failed: {str(e)}",
            "details": {"tool_name": tool_name, "version": version, "error": str(e)}
        }
