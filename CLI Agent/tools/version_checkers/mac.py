"""
Mac Tool Version Checker

This file helps check what version of development tools are installed on Mac computers.

What it does:
1. Takes a tool name from the user (like "vscode" or "docker")
2. Asks our AI helper to find the correct Homebrew name
3. Uses Homebrew to check what version is installed
4. Reports the version or says if it's not installed

Think of it like asking "What version of this app do I have?"
"""

import subprocess
import shutil
import logging
from tools.utils.llm_homebrew_resolver import resolve_for_version_check

# Set up logging so we can see what happens
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_active_version(tool_name):
    """
    Check what version of a tool is currently active in the PATH.
    
    This directly runs the tool's version command to see what's currently being used.
    """
    try:
        # Map common tool names to their version commands
        version_commands = {
            "java": ["java", "-version"],
            "node": ["node", "--version"],
            "python": ["python3", "--version"],
            "python3": ["python3", "--version"],
            "npm": ["npm", "--version"],
            "docker": ["docker", "--version"],
        }
        
        # Get the appropriate version command
        cmd = version_commands.get(tool_name.lower())
        if not cmd:
            # Default: try tool_name --version
            cmd = [tool_name, "--version"]
        
        # Run the version command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            output = result.stdout.strip() or result.stderr.strip()  # Some tools output to stderr
            # Extract version from output
            version = extract_version_from_output(output, tool_name)
            return {
                "found": True,
                "version": version,
                "raw_output": output
            }
        else:
            return {"found": False}
            
    except Exception as e:
        logger.info(f"Could not check active version for {tool_name}: {e}")
        return {"found": False}

def extract_version_from_output(output, tool_name):
    """Extract version number from tool version output."""
    import re
    
    # Common version patterns
    patterns = [
        r'version "([^"]+)"',  # Java: openjdk version "21.0.8"
        r'v(\d+\.\d+\.\d+)',   # Node: v20.1.0
        r'(\d+\.\d+\.\d+)',    # Generic: 3.12.0
        r'version (\d+\.\d+\.\d+)', # Docker: version 20.10.8
    ]
    
    for pattern in patterns:
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            return match.group(1)
    
    # If no pattern matches, return first line (cleaned up)
    first_line = output.split('\n')[0].strip()
    return first_line

def match_active_version_to_package(active_info, primary_package, alternatives):
    """
    Try to match the active version to a specific Homebrew package.
    
    This helps identify which exact package (e.g., openjdk@21 vs openjdk@17) is currently active.
    """
    version = active_info.get("version", "")
    
    # For Java, try to match version to package name
    if "java" in primary_package.lower() or "openjdk" in primary_package.lower() or any("java" in alt.lower() or "openjdk" in alt.lower() for alt in alternatives):
        # Extract major version number
        import re
        version_match = re.search(r'^(\d+)', version)
        if version_match:
            major_version = version_match.group(1)
            
            # Check if there's a version-specific package
            version_specific = f"openjdk@{major_version}"
            all_packages = [primary_package] + alternatives
            
            if version_specific in all_packages:
                return version_specific
    
    # For other tools, could add similar logic
    
    # Default to primary package
    return primary_package

def check_version_mac_tool(tool_name):
    """
    Check what version of a development tool is installed on Mac.
    
    This is the main function that does all the work.
    
    Args:
        tool_name: The name of the tool to check (like "cursor" or "docker")
    
    Returns:
        A dictionary with:
        - status: "success" if we found it, "error" if we didn't
        - message: What happened
        - version: The version that's installed (if any)
        - details: Extra information about what we found
    """
    logger.info(f"Starting Mac version check: {tool_name}")
    
    # Step 1: Check if Homebrew is installed
    if not shutil.which("brew"):
        return {
            "status": "error",
            "message": "Homebrew is not installed. Cannot check tool versions without Homebrew."
        }
    
    # Step 2: Ask our AI helper to find the correct package name
    logger.info("Asking AI helper to find the correct package name...")
    ai_result = resolve_for_version_check(tool_name)
    
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
    
    logger.info(f"AI helper found: '{tool_name}' should be checked as '{package_name}' (GUI app: {is_cask}, confidence: {confidence})")
    if alternatives:
        logger.info(f"Alternative packages to try: {alternatives}")
    
    # Step 4: First check what version is currently active in PATH
    active_version_info = check_active_version(tool_name)
    if active_version_info.get("found", False):
        logger.info(f"Found active {tool_name} version in PATH: {active_version_info['version']}")
        # Try to match the active version to a Homebrew package
        detected_package = match_active_version_to_package(active_version_info, package_name, alternatives)
        logger.info(f"Matched active version to package: {detected_package}")
        return {
            "status": "success", 
            "message": f"{tool_name} ({detected_package}) is installed",
            "version": active_version_info["version"],
            "details": {
                "requested_tool": tool_name,
                "package": detected_package,
                "type": "command line tool",
                "ai_confidence": confidence,
                "version_details": active_version_info["raw_output"],
                "source": "active_in_path"
            }
        }
    
    # Step 5: If no active version found, check installed packages - try primary package first
    version_info = get_installed_version(package_name, is_cask)
    
    # Step 6: If primary package not found, try alternatives
    if not version_info.get("installed", False) and alternatives:
        logger.info(f"Primary package '{package_name}' not found, trying alternatives...")
        for alt_package in alternatives:
            logger.info(f"Trying alternative: {alt_package}")
            alt_version_info = get_installed_version(alt_package, is_cask)
            if alt_version_info.get("installed", False):
                logger.info(f"Found installed alternative: {alt_package}")
                version_info = alt_version_info
                package_name = alt_package  # Update package_name for response
                break
    
    if version_info["installed"]:
        logger.info(f"Found {package_name} version: {version_info['version']}")
        return {
            "status": "success",
            "message": f"{tool_name} ({package_name}) is installed",
            "version": version_info["version"],
            "details": {
                "requested_tool": tool_name,
                "package": package_name,
                "type": "GUI app" if is_cask else "command line tool",
                "ai_confidence": confidence,
                "version_details": version_info["raw_output"]
            }
        }
    else:
        logger.info(f"{package_name} is not installed")
        return {
            "status": "error",
            "message": f"{tool_name} ({package_name}) is not installed",
            "version": None,
            "details": {
                "requested_tool": tool_name,
                "package": package_name,
                "action": "not_installed"
            }
        }

def get_installed_version(tool_name, is_cask=False):
    """
    Get the version of a tool that's installed via Homebrew.
    
    Args:
        tool_name: The Homebrew package name
        is_cask: True if it's a GUI app, False if it's a command line tool
    
    Returns:
        A dictionary with:
        - installed: True if the tool is installed, False if not
        - version: The version string (if installed)
        - raw_output: The raw output from Homebrew
    """
    try:
        # First check if it's installed at all
        if is_cask:
            list_command = ["brew", "list", "--cask", tool_name]
        else:
            list_command = ["brew", "list", tool_name]
        
        list_result = subprocess.run(
            list_command,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # If it's not installed, return early
        if list_result.returncode != 0:
            return {
                "installed": False,
                "version": None,
                "raw_output": list_result.stderr.strip() or "Not installed"
            }
        
        # Now get version information
        if is_cask:
            version_command = ["brew", "list", "--cask", "--versions", tool_name]
        else:
            version_command = ["brew", "list", "--versions", tool_name]
        
        version_result = subprocess.run(
            version_command,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if version_result.returncode == 0:
            version_output = version_result.stdout.strip()
            # Extract version from output like "tool_name version_number"
            parts = version_output.split()
            if len(parts) >= 2:
                version = " ".join(parts[1:])  # Everything after tool name
            else:
                version = version_output
            
            return {
                "installed": True,
                "version": version,
                "raw_output": version_output
            }
        else:
            # It's installed but we can't get version info
            return {
                "installed": True,
                "version": "unknown",
                "raw_output": version_result.stderr.strip() or "Version unknown"
            }
            
    except subprocess.TimeoutExpired:
        logger.warning(f"Version check for {tool_name} took too long")
        return {
            "installed": False,
            "version": None,
            "raw_output": "Timeout while checking version"
        }
    except Exception as e:
        logger.warning(f"Error checking version of {tool_name}: {e}")
        return {
            "installed": False,
            "version": None,
            "raw_output": f"Error: {str(e)}"
        }

def check_if_tool_installed(tool_name, is_cask=False):
    """
    Simple check if a tool is installed (without version info).
    
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
def check_version_tool_mac(tool):
    """Old function name - use check_version_mac_tool instead"""
    return check_version_mac_tool(tool)
