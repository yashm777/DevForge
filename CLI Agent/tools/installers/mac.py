"""
Mac Tool Installer

This file helps install development tools on Mac computers using Homebrew.

What it does:
1. Takes a tool name from the user (like "vscode" or "docker")
2. Asks our AI helper to find the correct Homebrew name
3. Uses Homebrew to install the tool
4. Reports if it worked or not

Think of it like a smart shopping assistant that knows where to find everything in the store.
"""

import subprocess
import shutil
import logging
from tools.utils.llm_homebrew_resolver import resolve_for_install, enhance_package_with_version

# Set up logging so we can see what happens
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def install_mac_tool(tool_name, version="latest"):
    """
    Install a development tool on Mac using Homebrew.
    
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
    
    # Step 1: Check if Homebrew is installed
    if not shutil.which("brew"):
        return {
            "status": "error",
            "message": "Homebrew is not installed. Please install Homebrew first."
        }
    
    # Step 2: Ask our AI helper to find the correct package name
    logger.info("Asking AI helper to find the correct package name...")
    ai_result = resolve_for_install(tool_name, version)
    
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
    
    logger.info(f"AI helper found: '{tool_name}' should be installed as '{package_name}' (GUI app: {is_cask}, confidence: {confidence})")
    
    # Step 4: Add version to package name if needed
    final_package_name = enhance_package_with_version(package_name, version)
    
    # Step 5: Try to install the tool
    try:
        # Create the install command
        if is_cask:
            # For GUI apps, use: brew install --cask packagename
            command = ["brew", "install", "--cask", final_package_name]
        else:
            # For command line tools, use: brew install packagename
            command = ["brew", "install", final_package_name]
        
        logger.info(f"Running command: {' '.join(command)}")
        
        # Run the command and wait for it to finish
        result = subprocess.run(
            command,
            capture_output=True,  # Capture what the command prints
            text=True,           # Give us text instead of bytes
            timeout=600          # Wait up to 10 minutes
        )
        
        # Step 6: Check if the install worked
        if result.returncode == 0:
            logger.info(f"Successfully installed {final_package_name}")
            
            # Step 7: Handle path updates and shell refresh for command line tools
            refresh_commands = []
            path_updated = False
            
            if not is_cask:  # Only command line tools need path updates
                # Check if we need to update paths after installation
                path_update_result = update_tool_path_after_install(final_package_name, tool_name)
                if path_update_result["path_updated"]:
                    path_updated = True
                    refresh_commands = path_update_result["refresh_commands"]
            
            success_message = f"Successfully installed {tool_name} ({final_package_name})"
            if refresh_commands:
                success_message += f"\n\nIMPORTANT: To use the new tool, run these commands in your terminal:\n" + "\n".join(refresh_commands)
            
            return {
                "status": "success",
                "message": success_message,
                "details": {
                    "requested_tool": tool_name,
                    "installed_package": final_package_name,
                    "type": "GUI app" if is_cask else "command line tool",
                    "command_used": " ".join(command),
                    "ai_confidence": confidence,
                    "path_updated": path_updated,
                    "refresh_commands": refresh_commands
                }
            }
        else:
            # Something went wrong
            error_output = result.stderr.strip() or result.stdout.strip()
            
            # Check if it's already installed
            if "already installed" in error_output.lower():
                logger.info(f"{final_package_name} is already installed")
                return {
                    "status": "success",
                    "message": f"{tool_name} ({final_package_name}) is already installed",
                    "details": {
                        "requested_tool": tool_name,
                        "package": final_package_name,
                        "action": "already_installed"
                    }
                }
            
            logger.error(f"Install failed: {error_output}")
            return {
                "status": "error",
                "message": f"Failed to install {tool_name} ({final_package_name}): {error_output}",
                "details": {
                    "requested_tool": tool_name,
                    "package": final_package_name,
                    "error": error_output
                }
            }
            
    except subprocess.TimeoutExpired:
        # The command took too long
        logger.error(f"Install of {final_package_name} took too long")
        return {
            "status": "error",
            "message": f"Install of {tool_name} ({final_package_name}) timed out after 10 minutes"
        }
    except Exception as e:
        # Something unexpected happened
        logger.error(f"Unexpected error during install: {e}")
        return {
            "status": "error",
            "message": f"Install failed with unexpected error: {str(e)}"
        }

def check_if_tool_exists(tool_name, is_cask=False):
    """
    Check if a tool is available in Homebrew without installing it.
    
    This is like checking if a store has an item before trying to buy it.
    
    Args:
        tool_name: The Homebrew package name
        is_cask: True if it's a GUI app, False if it's a command line tool
    
    Returns:
        True if the tool exists in Homebrew, False if not
    """
    try:
        if is_cask:
            command = ["brew", "info", "--cask", tool_name]
        else:
            command = ["brew", "info", tool_name]
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30  # 30 seconds should be enough
        )
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        logger.warning(f"Checking if {tool_name} exists took too long")
        return False
    except Exception as e:
        logger.warning(f"Error checking if {tool_name} exists: {e}")
        return False

def check_if_tool_installed(tool_name, is_cask=False):
    """
    Check if a tool is already installed on this computer.
    
    Args:
        tool_name: The Homebrew package name
        is_cask: True if it's a GUI app, False if it's a command line tool
    
    Returns:
        True if already installed, False if not
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

# Keep the old function name for compatibility
def install_tool_mac(tool, version="latest"):
    """Old function name - use install_mac_tool instead"""
    return install_mac_tool(tool, version)

def update_tool_path_after_install(package_name, tool_name):
    """
    Update PATH and shell configuration after installing a command line tool.
    
    After installing tools like Node.js, Python, etc., we need to tell the user
    how to refresh their terminal so the new tool is in their PATH.
    
    Args:
        package_name: The Homebrew package name that was installed
        tool_name: The original tool name user requested
    
    Returns:
        Dictionary with:
        - path_updated: True if path needs updating
        - refresh_commands: List of commands user should run
    """
    logger.info(f"Checking if {package_name} needs path updates after installation")
    
    # Tools that commonly need path updates after installation
    tools_needing_path_update = {
        "node": "Node.js",
        "python": "Python", 
        "python3": "Python 3",
        "go": "Go",
        "rust": "Rust",
        "java": "Java",
        "openjdk": "OpenJDK",
        "ruby": "Ruby",
        "php": "PHP",
        "kotlin": "Kotlin",
        "scala": "Scala",
        "maven": "Maven",
        "gradle": "Gradle"
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
    
    # Generate shell refresh commands
    refresh_commands = [
        "# Refresh your terminal to use the new tool:",
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
