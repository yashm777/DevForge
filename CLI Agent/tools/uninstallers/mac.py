"""
Mac Tool Uninstaller

This file helps remove development tools from Mac computers using Homebrew.

What it does:
1. Takes a tool name from the user (like "vscode" or "docker")
2. Asks our AI helper to find the correct Homebrew name
3. Uses Homebrew to remove the tool
4. Reports if it worked or not

Think of it like a smart cleaning assistant that knows how to properly remove things.
"""

import subprocess
import shutil
import logging
from tools.utils.llm_homebrew_resolver import resolve_for_uninstall

# Set up logging so we can see what happens
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def uninstall_mac_tool(tool_name):
    """
    Remove a development tool from Mac using Homebrew.
    
    This is the main function that does all the work.
    
    Args:
        tool_name: The name of the tool the user wants to remove (like "cursor" or "docker")
    
    Returns:
        A dictionary with:
        - status: "success" if it worked, "error" if it didn't
        - message: What happened
        - details: Extra information about what we did
    """
    logger.info(f"Starting Mac uninstall: {tool_name}")
    
    # Step 1: Check if Homebrew is installed
    if not shutil.which("brew"):
        return {
            "status": "error",
            "message": "Homebrew is not installed. Cannot uninstall tools without Homebrew."
        }
    
    # Step 2: Ask our AI helper to find the correct package name
    logger.info("Asking AI helper to find the correct package name...")
    ai_result = resolve_for_uninstall(tool_name)
    
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
    
    logger.info(f"AI helper found: '{tool_name}' should be uninstalled as '{package_name}' (GUI app: {is_cask}, confidence: {confidence})")
    
    # Step 4: Check if the tool is actually installed
    if not check_if_tool_installed(package_name, is_cask):
        logger.info(f"Tool '{package_name}' is not installed")
        return {
            "status": "error",
            "message": f"{tool_name} ({package_name}) is not installed, so it cannot be uninstalled.",
            "details": {
                "requested_tool": tool_name,
                "package": package_name,
                "action": "not_installed"
            }
        }
    
    # Step 5: Try to uninstall the tool
    try:
        # Create the uninstall command
        if is_cask:
            # For GUI apps, use: brew uninstall --cask packagename
            command = ["brew", "uninstall", "--cask", package_name]
        else:
            # For command line tools, use: brew uninstall packagename
            command = ["brew", "uninstall", package_name]
        
        logger.info(f"Running command: {' '.join(command)}")
        
        # Run the command and wait for it to finish
        result = subprocess.run(
            command,
            capture_output=True,  # Capture what the command prints
            text=True,           # Give us text instead of bytes
            timeout=300          # Wait up to 5 minutes
        )
        
        # Step 6: Check if the uninstall worked
        if result.returncode == 0:
            logger.info(f"Successfully uninstalled {package_name}")
            return {
                "status": "success",
                "message": f"Successfully uninstalled {tool_name} ({package_name})",
                "details": {
                    "requested_tool": tool_name,
                    "uninstalled_package": package_name,
                    "type": "GUI app" if is_cask else "command line tool",
                    "command_used": " ".join(command),
                    "ai_confidence": confidence
                }
            }
        else:
            # Something went wrong
            error_output = result.stderr.strip() or result.stdout.strip()
            
            # Check if it was already uninstalled
            if "not installed" in error_output.lower():
                logger.info(f"{package_name} was not installed")
                return {
                    "status": "success",
                    "message": f"{tool_name} ({package_name}) was not installed, so nothing to uninstall",
                    "details": {
                        "requested_tool": tool_name,
                        "package": package_name,
                        "action": "was_not_installed"
                    }
                }
            
            logger.error(f"Uninstall failed: {error_output}")
            return {
                "status": "error",
                "message": f"Failed to uninstall {tool_name} ({package_name}): {error_output}",
                "details": {
                    "requested_tool": tool_name,
                    "package": package_name,
                    "error": error_output
                }
            }
            
    except subprocess.TimeoutExpired:
        # The command took too long
        logger.error(f"Uninstall of {package_name} took too long")
        return {
            "status": "error",
            "message": f"Uninstall of {tool_name} ({package_name}) timed out after 5 minutes"
        }
    except Exception as e:
        # Something unexpected happened
        logger.error(f"Unexpected error during uninstall: {e}")
        return {
            "status": "error",
            "message": f"Uninstall failed with unexpected error: {str(e)}"
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

# Keep the old function name for compatibility
def uninstall_tool_mac(tool):
    """Old function name - use uninstall_mac_tool instead"""
    return uninstall_mac_tool(tool)
