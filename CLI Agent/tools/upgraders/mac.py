"""
Mac Tool Upgrader - Clean and Simple

This module handles upgrading tools on Mac using the MacToolManager.
"""

import logging
from tools.utils.mac_tool_manager import get_manager
from tools.utils.name_resolver import resolve_tool_name

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_post_upgrade_instructions(tool_name: str, version: str) -> str:
    """
    Generate helpful post-upgrade instructions for common development tools.
    
    Args:
        tool_name: Name of the upgraded tool
        version: Version that was installed
        
    Returns:
        String with helpful instructions or empty string if no specific instructions
    """
    tool_base = tool_name.split('@')[0].lower()
    
    instructions = {
        'node': f"• Verify: `node --version` should show v{version}\n• Use: `npm install -g <package>` to install global packages\n• Consider using `nvm` for managing multiple Node.js versions",
        'python': f"• Verify: `python3 --version` should show {version}\n• Use: `pip3 install <package>` to install packages\n• Consider using `pyenv` for managing multiple Python versions",
        'java': f"• Verify: `java --version` should show {version}\n• Set JAVA_HOME: `export JAVA_HOME=/opt/homebrew/Cellar/openjdk@{version.split('.')[0]}/{version}/libexec/openjdk.jdk/Contents/Home`\n• Add to ~/.zshrc: `echo 'export JAVA_HOME=/opt/homebrew/Cellar/openjdk@{version.split('.')[0]}/{version}/libexec/openjdk.jdk/Contents/Home' >> ~/.zshrc`",
        'openjdk': f"• Verify: `java --version` should show OpenJDK {version}\n• Set JAVA_HOME: `export JAVA_HOME=/opt/homebrew/Cellar/openjdk@{version.split('.')[0]}/{version}/libexec/openjdk.jdk/Contents/Home`\n• Add to ~/.zshrc: `echo 'export JAVA_HOME=/opt/homebrew/Cellar/openjdk@{version.split('.')[0]}/{version}/libexec/openjdk.jdk/Contents/Home' >> ~/.zshrc`",
        'go': f"• Verify: `go version` should show {version}\n• Create your first project: `go mod init myproject`\n• Build projects: `go build` or `go run main.go`",
        'docker': f"• Verify: `docker --version` should show {version}\n• Start Docker daemon if needed\n• Try: `docker run hello-world` to test installation",
        'git': f"• Verify: `git --version` should show {version}\n• Configure: `git config --global user.name \"Your Name\"`\n• Configure: `git config --global user.email \"your@email.com\"`",
        'rust': f"• Verify: `rustc --version` should show {version}\n• Create project: `cargo new myproject`\n• Build: `cargo build` or run: `cargo run`",
        'kotlin': f"• Verify: `kotlin -version` should show {version}\n• Compile: `kotlinc hello.kt -include-runtime -d hello.jar`\n• Run: `java -jar hello.jar`"
    }
    
    return instructions.get(tool_base, "")

def upgrade_mac_tool(tool_name, version="latest"):
    """
    Upgrade a tool on Mac to the latest or specified version.
    
    Args:
        tool_name: Name of the tool to upgrade
        version: Target version (defaults to latest)
    
    Returns:
        Dictionary with status, message, and details
    """
    logger.info(f"Starting Mac upgrade: {tool_name} to version {version}")
    
    try:
        # Resolve tool name for Mac system (handles Linux package names)
        resolved = resolve_tool_name(tool_name, "darwin", version, "install")
        resolved_tool_name = resolved["name"]
        logger.info(f"Resolved '{tool_name}' to '{resolved_tool_name}' for Mac upgrade")
        
        # Use the comprehensive tool manager (MacToolManager.upgrade_tool only takes tool_name)
        manager = get_manager()
        result = manager.upgrade_tool(resolved_tool_name)
        
        # Enhance successful results with post-upgrade instructions
        if result.get("status") == "success" and "new_version" in result:
            instructions = get_post_upgrade_instructions(resolved_tool_name, result["new_version"])
            if instructions:
                result["instructions"] = instructions
                result["message"] = f"{result['message']}\n\nNext steps:\n{instructions}"
        
        return result
        
    except Exception as e:
        logger.error(f"Upgrade failed for {tool_name}: {e}")
        return {
            "status": "error",
            "message": f"Upgrade failed: {str(e)}",
            "details": {"tool_name": tool_name, "error": str(e)}
        }

def downgrade_mac_tool(tool_name, target_version=None):
    """
    Downgrade a development tool on Mac (currently same as upgrade).
    
    Args:
        tool_name: The name of the tool to downgrade
        target_version: Optional specific version to downgrade to
    
    Returns:
        Dictionary with status, message, and details
    """
    logger.info(f"Starting downgrade process for tool: {tool_name}")
    
    # For now, this uses the same logic as upgrade but with different messaging
    result = upgrade_mac_tool(tool_name)
    
    # Update the messaging for downgrade context
    if result.get("status") == "success":
        result["message"] = result["message"].replace("upgraded", "switched to")
    
    return result

# Legacy function aliases for backwards compatibility
def handle_tool(tool_name, version="latest"):
    """Legacy function name - use upgrade_mac_tool instead."""
    return upgrade_mac_tool(tool_name, version)
