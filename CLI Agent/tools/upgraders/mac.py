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
    
    # Check if this is a versioned package
    is_versioned = '@' in tool_name
    
    # Special handling for Java with dynamic path detection
    if tool_base in ['java', 'openjdk']:
        # Use brew --prefix to get the actual installation path
        try:
            import subprocess
            result = subprocess.run(
                ["brew", "--prefix", tool_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                brew_prefix = result.stdout.strip()
                java_home = f"{brew_prefix}/libexec/openjdk.jdk/Contents/Home"
                
                return f"• Verify: `{brew_prefix}/bin/java --version` should show {version}\n• Set JAVA_HOME: `export JAVA_HOME={java_home}`\n• Add to ~/.zshrc: `echo 'export JAVA_HOME={java_home}' >> ~/.zshrc`"
            else:
                # Fallback to generic instruction
                return f"• Check installation: `brew --prefix {tool_name}`\n• Set JAVA_HOME based on the output path + '/libexec/openjdk.jdk/Contents/Home'"
                
        except Exception:
            return f"• Installation complete. Run `brew --prefix {tool_name}` to get the correct JAVA_HOME path"
    
    if is_versioned:
        # Special instructions for versioned packages
        if tool_base == 'node':
            return f"• Verify: `/opt/homebrew/opt/{tool_name}/bin/node --version` should show v{version}\n• This is {tool_name} (specific version)\n• To use this version: add `/opt/homebrew/opt/{tool_name}/bin` to your PATH\n• Or use `nvm` to manage multiple Node.js versions"
        elif tool_base == 'python':
            return f"• Verify: `/opt/homebrew/opt/{tool_name}/bin/python3 --version` should show {version}\n• This is {tool_name} (specific version)\n• To use this version: add `/opt/homebrew/opt/{tool_name}/bin` to your PATH\n• Or use `pyenv` to manage multiple Python versions"
        else:
            return f"• This is {tool_name} (specific version)\n• Check: `/opt/homebrew/opt/{tool_name}/bin/{tool_base} --version`\n• Add to PATH to use: `export PATH=\"/opt/homebrew/opt/{tool_name}/bin:$PATH\"`"
    
    # Regular instructions for non-versioned packages
    instructions = {
        'node': f"• Verify: `node --version` should show v{version}\n• Use: `npm install -g <package>` to install global packages\n• Consider using `nvm` for managing multiple Node.js versions",
        'python': f"• Verify: `python3 --version` should show {version}\n• Use: `pip3 install <package>` to install packages\n• Consider using `pyenv` for managing multiple Python versions",
        'go': f"• Verify: `go version` should show {version}\n• Create your first project: `go mod init myproject`\n• Build projects: `go build` or `go run main.go`",
        'docker': f"• Verify: `docker --version` should show {version}\n• Start Docker daemon if needed\n• Try: `docker run hello-world` to test installation",
        'git': f"• Verify: `git --version` should show {version}\n• Configure: `git config --global user.name \"Your Name\"`\n• Configure: `git config --global user.email \"your@email.com\"`",
        'rust': f"• Verify: `rustc --version` should show {version}\n• Create project: `cargo new myproject`\n• Build: `cargo build` or run: `cargo run`",
        'kotlin': f"• Verify: `kotlin -version` should show {version}\n• Compile: `kotlinc hello.kt -include-runtime -d hello.jar`\n• Run: `java -jar hello.jar`"
    }
    
    return instructions.get(tool_base, "")

def upgrade_mac_tool(tool_name, version="latest"):
    """
    Upgrade a tool on Mac to the latest version (simplified).
    """
    logger.info(f"Starting Mac upgrade: {tool_name} to latest version")
    
    try:
        # Resolve tool name for Mac system
        resolved = resolve_tool_name(tool_name, "darwin", version, "install")
        resolved_tool_name = resolved["name"]
        
        manager = get_manager()
        
        # Simple upgrade to latest - no version complexity
        result = manager.upgrade_tool(resolved_tool_name)
        
        # Add post-upgrade instructions if successful
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
            "message": f"Upgrade failed: {str(e)}"
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
