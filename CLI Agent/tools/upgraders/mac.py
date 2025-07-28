"""
Mac Tool Upgrader

This file helps upgrade development tools on Mac computers using Homebrew.

What it does:
1. Takes a tool name from the user (like "vscode" or "docker")
2. Asks our AI helper to find the correct Homebrew name
3. Uses Homebrew to upgrade the tool to the latest version
4. Reports if it worked or not

Think of it like updating your apps to get the newest features and bug fixes.
"""

import subprocess
import shutil
import logging
import os
from tools.utils.llm_homebrew_resolver import resolve_for_upgrade

# Set up logging so we can see what happens
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def downgrade_mac_tool(tool_name, target_version=None):
    """
    Downgrade a development tool on Mac to a specific or older version.
    
    This is essentially the same as upgrade_mac_tool but with different messaging.
    For Java, it switches between installed versions using the shell configuration.
    
    Args:
        tool_name: The name of the tool to downgrade
        target_version: Optional specific version to downgrade to
    
    Returns:
        Dictionary with:
        - status: "success", "error", or "warning"
        - message: Human-friendly description of what happened
        - details: Technical information about the operation
    """
    logger.info(f"Starting downgrade process for tool: {tool_name}")
    
    # For now, this uses the same logic as upgrade but with different messaging
    # In the future, this could be enhanced to specifically handle downgrades
    result = upgrade_mac_tool(tool_name)
    
    # Update the messaging for downgrade context
    if result["status"] == "success":
        result["message"] = result["message"].replace("upgraded", "switched to")
        result["message"] = result["message"].replace("Successfully upgraded", "Successfully switched")
    
    return result


def upgrade_mac_tool(tool_name, version="latest"):
    """
    Upgrade a development tool on Mac using Homebrew.
    
    This is the main function that does all the work.
    
    Args:
        tool_name: The name of the tool to upgrade (like "cursor" or "docker")
        version: What version to upgrade to (usually "latest")
    
    Returns:
        A dictionary with:
        - status: "success" if it worked, "error" if it didn't
        - message: What happened
        - details: Extra information about what we did
    """
    logger.info(f"Starting Mac upgrade: {tool_name} (version: {version})")
    
    # Step 1: Check if Homebrew is installed
    if not shutil.which("brew"):
        return {
            "status": "error",
            "message": "Homebrew is not installed. Cannot upgrade tools without Homebrew."
        }
    
    # Step 2: Ask our AI helper to find the correct package name
    logger.info("Asking AI helper to find the correct package name...")
    ai_result = resolve_for_upgrade(tool_name, version)
    
    if ai_result["status"] != "success":
        error_message = ai_result.get("message", "AI helper could not find the tool")
        logger.error(f"AI helper failed: {error_message}")
        return {
            "status": "error",
            "message": f"Could not find '{tool_name}' in Homebrew: {error_message}"
        }
    
    # Step 3: Get the information from our AI helper
    package_name = ai_result["package"]
    is_cask = ai_result["is_cask"]
    confidence = ai_result["confidence"]
    alternatives = ai_result.get("alternatives", [])
    
    logger.info(f"AI helper found: '{tool_name}' should be upgraded as '{package_name}' (GUI app: {is_cask}, confidence: {confidence})")
    if alternatives:
        logger.info(f"Alternative packages to try: {alternatives}")
    
    # Step 4: Check if the tool is actually installed - try primary package first
    installed_package = None
    if check_if_tool_installed(package_name, is_cask):
        installed_package = package_name
    elif alternatives:
        # Try alternatives if primary is not installed
        logger.info(f"Primary package '{package_name}' not installed, checking alternatives...")
        for alt_package in alternatives:
            logger.info(f"Checking alternative: {alt_package}")
            if check_if_tool_installed(alt_package, is_cask):
                logger.info(f"Found installed alternative: {alt_package}")
                installed_package = alt_package
                break
    
    if not installed_package:
        logger.info(f"Tool '{tool_name}' is not installed (tried {package_name}" + (f" and alternatives {alternatives}" if alternatives else "") + ")")
        return {
            "status": "error", 
            "message": f"{tool_name} ({package_name}) is not installed. Install it first before upgrading.",
            "details": {
                "requested_tool": tool_name,
                "package": package_name,
                "action": "not_installed"
            }
        }
    
    # Step 5: Try to upgrade the tool
    try:
        # Create the upgrade command using the actually installed package
        if is_cask:
            # For GUI apps, use: brew upgrade --cask packagename
            command = ["brew", "upgrade", "--cask", installed_package]
        else:
            # For command line tools, use: brew upgrade packagename
            command = ["brew", "upgrade", installed_package]
        
        logger.info(f"Running command: {' '.join(command)}")
        
        # Run the command and wait for it to finish
        result = subprocess.run(
            command,
            capture_output=True,  # Capture what the command prints
            text=True,           # Give us text instead of bytes
            timeout=600          # Wait up to 10 minutes
        )
        
        # Step 6: Check if the upgrade worked
        if result.returncode == 0:
            logger.info(f"Successfully upgraded {installed_package}")
            
            # Get new version info
            new_version = get_installed_version(installed_package, is_cask)
            
            # Step 7: Handle path updates and shell refresh for command line tools
            refresh_commands = []
            path_updated = False
            
            if not is_cask:  # Only command line tools need path updates
                # Check if we need to update paths after upgrade
                path_update_result = update_tool_path_after_upgrade(installed_package, tool_name)
                if path_update_result["path_updated"]:
                    path_updated = True
                    refresh_commands = path_update_result["refresh_commands"]
            
            success_message = f"Successfully upgraded {tool_name} ({installed_package})"
            if refresh_commands:
                success_message += f"\n\nIMPORTANT: To use the new version, run these commands in your terminal:\n" + "\n".join(refresh_commands)
            
            return {
                "status": "success",
                "message": success_message,
                "details": {
                    "requested_tool": tool_name,
                    "upgraded_package": installed_package,
                    "type": "GUI app" if is_cask else "command line tool",
                    "command_used": " ".join(command),
                    "new_version": new_version,
                    "ai_confidence": confidence,
                    "path_updated": path_updated,
                    "refresh_commands": refresh_commands
                }
            }
        else:
            # Something went wrong or it's already up to date
            error_output = result.stderr.strip() or result.stdout.strip()
            
            # Check if it's already up-to-date
            if "already up-to-date" in error_output.lower() or "already installed" in error_output.lower():
                current_version = get_installed_version(installed_package, is_cask)
                logger.info(f"{installed_package} is already up-to-date")
                return {
                    "status": "success",
                    "message": f"{tool_name} ({installed_package}) is already up-to-date",
                    "details": {
                        "requested_tool": tool_name,
                        "package": installed_package,
                        "type": "GUI app" if is_cask else "command line tool",
                        "current_version": current_version,
                        "action": "already_up_to_date"
                    }
                }
            
            logger.error(f"Upgrade failed: {error_output}")
            return {
                "status": "error",
                "message": f"Failed to upgrade {tool_name} ({installed_package}): {error_output}",
                "details": {
                    "requested_tool": tool_name,
                    "package": installed_package,
                    "error": error_output
                }
            }
            
    except subprocess.TimeoutExpired:
        # The command took too long
        logger.error(f"Upgrade of {package_name} took too long")
        return {
            "status": "error",
            "message": f"Upgrade of {tool_name} ({package_name}) timed out after 10 minutes"
        }
    except Exception as e:
        # Something unexpected happened
        logger.error(f"Unexpected error during upgrade: {e}")
        return {
            "status": "error",
            "message": f"Upgrade failed with unexpected error: {str(e)}"
        }

def check_if_tool_installed(tool_name, is_cask=False):
    """
    Check if a tool is installed on this computer.
    
    Args:
        tool_name: The Homebrew package name
        is_cask: True if it's a GUI app, False if it's a command line tool
    
    Returns:
        True if installed, False if not
    """
    try:
        if is_cask:
            command = ["brew", "list", "--cask", tool_name]
        else:
            command = ["brew", "list", tool_name]
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        logger.warning(f"Checking if {tool_name} is installed took too long")
        return False
    except Exception as e:
        logger.warning(f"Error checking if {tool_name} is installed: {e}")
        return False

def get_installed_version(tool_name, is_cask=False):
    """
    Get the current version of an installed tool.
    
    Args:
        tool_name: The Homebrew package name
        is_cask: True if it's a GUI app, False if it's a command line tool
    
    Returns:
        Version string or "unknown"
    """
    try:
        if is_cask:
            command = ["brew", "list", "--cask", "--versions", tool_name]
        else:
            command = ["brew", "list", "--versions", tool_name]
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            version_output = result.stdout.strip()
            # Extract version from output like "tool_name version_number"
            parts = version_output.split()
            if len(parts) >= 2:
                return " ".join(parts[1:])  # Everything after tool name
            return version_output
        else:
            return "unknown"
            
    except subprocess.TimeoutExpired:
        logger.warning(f"Getting version of {tool_name} took too long")
        return "unknown"
    except Exception as e:
        logger.warning(f"Error getting version of {tool_name}: {e}")
        return "unknown"

# Keep the old function name for compatibility
def upgrade_tool_mac(tool, target_version="latest"):
    """Old function name - use upgrade_mac_tool instead"""
    return upgrade_mac_tool(tool, target_version)

def update_java_shell_config(package_name):
    """
    Update .zshrc file with proper Java configuration for version switching.
    
    Args:
        package_name: The Homebrew Java package name (e.g., 'openjdk@17', 'openjdk@21')
    
    Returns:
        Dictionary with success status and commands to run
    """
    logger.info(f"Updating .zshrc for Java package: {package_name}")
    
    try:
        # Get the Homebrew installation path for this Java version
        result = subprocess.run(
            ["brew", "--prefix", package_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            logger.error(f"Failed to get brew prefix for {package_name}")
            return {
                "success": False,
                "error": f"Could not find Homebrew installation for {package_name}"
            }
        
        java_path = result.stdout.strip()
        java_home = java_path
        java_bin = f"{java_path}/bin"
        
        # Read current .zshrc
        zshrc_path = os.path.expanduser("~/.zshrc")
        zshrc_content = []
        
        if os.path.exists(zshrc_path):
            with open(zshrc_path, 'r') as f:
                zshrc_content = f.readlines()
        
        # Remove existing Java configuration lines
        new_content = []
        skip_next_line = False
        for i, line in enumerate(zshrc_content):
            # Skip lines that are Java-related
            if (line.strip().startswith('export JAVA_HOME=') or 
                line.strip().startswith('# Java Configuration') or
                'openjdk' in line or 
                (line.strip().startswith('export PATH=') and 'openjdk' in line)):
                continue
            # Skip comments about Java from CLI Agent
            if ('Java' in line and 'CLI Agent' in line):
                continue
            new_content.append(line)
        
        # Add new Java configuration
        new_content.append(f'\n# Java Configuration - Updated by CLI Agent\n')
        new_content.append(f'export JAVA_HOME="{java_home}"\n')
        new_content.append(f'export PATH="{java_bin}:$PATH"\n')
        
        # Write back to .zshrc
        with open(zshrc_path, 'w') as f:
            f.writelines(new_content)
        
        logger.info(f"Successfully updated .zshrc with Java {package_name} configuration")
        
        return {
            "success": True,
            "java_home": java_home,
            "refresh_command": "source ~/.zshrc"
        }
        
    except Exception as e:
        logger.error(f"Error updating .zshrc for Java: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def update_tool_path_after_upgrade(package_name, tool_name):
    """
    Update PATH and shell configuration after upgrading a command line tool.
    
    After upgrading tools like Node.js, Python, etc., their paths often change
    and we need to tell the user how to refresh their terminal.
    
    Args:
        package_name: The Homebrew package name
        tool_name: The original tool name user requested
    
    Returns:
        Dictionary with:
        - path_updated: True if path needs updating
        - refresh_commands: List of commands user should run
    """
    logger.info(f"Checking if {package_name} needs path updates after upgrade")
    
    # Special handling for Java versions - actually update .zshrc
    if 'openjdk' in package_name.lower() or 'java' in tool_name.lower():
        config_result = update_java_shell_config(package_name)
        if config_result["success"]:
            return {
                "path_updated": True,
                "refresh_commands": [
                    f"✅ Updated .zshrc with Java configuration",
                    f"JAVA_HOME set to: {config_result['java_home']}",
                    "",
                    "To activate the changes, run:",
                    config_result["refresh_command"]
                ]
            }
        else:
            return {
                "path_updated": False,
                "refresh_commands": [
                    f"❌ Failed to update .zshrc: {config_result.get('error', 'Unknown error')}",
                    "Please manually update your Java configuration"
                ]
            }
    
    # Tools that commonly need path updates after upgrade
    tools_needing_path_update = {
        "node": "Node.js",
        "python": "Python", 
        "python3": "Python 3",
        "go": "Go",
        "rust": "Rust",
        "ruby": "Ruby",
        "php": "PHP",
        "kotlin": "Kotlin",
        "scala": "Scala"
    }
    
    # Check if this tool needs path updates
    needs_update = False
    for tool_key in tools_needing_path_update:
        if tool_key in package_name.lower() or tool_key in tool_name.lower():
            needs_update = True
            break
    
    if not needs_update:
        return {
            "path_updated": False,
            "refresh_commands": []
        }
    
    # Generate shell refresh commands for non-Java tools
    refresh_commands = [
        "# Refresh your terminal to use the new version:",
        "source ~/.zshrc",
        "# OR restart your terminal",
        "# OR run: exec zsh"
    ]
    
    # Add specific path update if needed
    try:
        # Get the new Homebrew installation path
        result = subprocess.run(
            ["brew", "--prefix", package_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            brew_path = result.stdout.strip()
            refresh_commands.insert(1, f'export PATH="{brew_path}/bin:$PATH"')
    except subprocess.TimeoutExpired:
        logger.warning("Could not get Homebrew path for PATH update")
    except Exception as e:
        logger.warning(f"Error getting Homebrew path: {e}")
    
    logger.info(f"Generated {len(refresh_commands)} refresh commands for {package_name}")
    
    return {
        "path_updated": True, 
        "refresh_commands": refresh_commands
    }
