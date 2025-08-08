"""
Comprehensive Mac Tool Management System

This module provides a production-ready, unified approach to managing development tools on macOS.
It addresses all the key pain points identified in the original system:

1. Accurate Python version detection (system vs virtual environment)
2. Proper tool vs application classification
3. Shell-aware configuration (bash/zsh)
4. Smart upgrade/downgrade logic
5. Version policy enforcement
6. Security and cleanup features
7. Performance optimizations

Usage:
    from tools.utils.mac_tool_manager import MacToolManager
    
    manager = MacToolManager()
    result = manager.install_tool("python@3.13.5")
    result = manager.check_version("python")
"""

import sys
import os
import subprocess
import json
import shutil
import re
import logging
from functools import lru_cache
from typing import Dict, List, Tuple, Optional, Set
from packaging.version import parse as parse_version

# Set up logging
logger = logging.getLogger(__name__)

class MacToolManager:
    """
    Comprehensive Mac tool management system that handles installation, upgrades,
    version checking, and configuration management for development tools.
    """
    
    # Tools that support version switching (command-line tools)
    UPGRADABLE_TOOLS = {
        'python', 'python3', 'java', 'node', 'ruby', 'php', 'go', 'rust',
        'git', 'docker', 'kubectl', 'terraform', 'ansible', 'maven', 'gradle',
        'npm', 'yarn', 'pip', 'cargo', 'composer', 'flutter', 'dart'
    }
    
    # System Python paths (bypass virtual environments)
    SYSTEM_PYTHON_PATHS = [
        '/usr/bin/python3',
        '/usr/local/bin/python3', 
        '/opt/homebrew/bin/python3',
        '/System/Library/Frameworks/Python.framework/Versions/Current/bin/python3',
    ]
    
    def __init__(self):
        """Initialize the Mac Tool Manager."""
        self._ensure_homebrew()
        
    def _ensure_homebrew(self) -> None:
        """Ensure Homebrew is installed."""
        if not shutil.which("brew"):
            raise RuntimeError(
                "Homebrew is not installed. Please install Homebrew first: "
                "/bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
            )
    
    # ==================== SYSTEM DETECTION ====================
    
    def get_system_python_executable(self) -> str:
        """
        Return the global Python3 executable, even if we're inside a venv.
        Falls back to common system paths and ultimately /usr/bin/python3.
        """
        # In a venv, base_prefix points to the real installation
        base = getattr(sys, "base_prefix", sys.prefix)
        candidates = [
            os.path.join(base, "bin", "python3"),
            *self.SYSTEM_PYTHON_PATHS
        ]
        
        for exe in candidates:
            if os.path.exists(exe):
                return exe
        
        # Last resort: rely on PATH
        return "python3"
    
    def get_system_python_version(self) -> str:
        """Get the system Python version, bypassing virtual environments."""
        exe = self.get_system_python_executable()
        try:
            result = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                output = result.stdout.strip() or result.stderr.strip()
                return self._extract_version_from_output(output)
        except Exception as e:
            logger.warning(f"Could not get system Python version: {e}")
        return "unknown"
    
    def in_virtualenv(self) -> bool:
        """Check if we're currently in a virtual environment."""
        return sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    
    def get_default_shell(self) -> str:
        """
        Read the user's login shell via dscl.
        Returns 'bash', 'zsh', or the detected shell name.
        """
        try:
            result = subprocess.run(
                ["dscl", ".", "-read", f"/Users/{os.getlogin()}", "UserShell"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                shell_path = result.stdout.strip().split()[-1]
                return os.path.basename(shell_path)
        except Exception as e:
            logger.debug(f"Could not detect shell via dscl: {e}")
        
        # Fallback to environment variable
        shell_env = os.environ.get("SHELL", "/bin/zsh")
        return os.path.basename(shell_env)
    
    def get_rc_file(self) -> str:
        """Get the appropriate shell configuration file path."""
        shell = self.get_default_shell()
        if shell == "bash":
            # Check which bash rc file exists
            for rc_file in ["~/.bash_profile", "~/.bashrc", "~/.profile"]:
                expanded = os.path.expanduser(rc_file)
                if os.path.exists(expanded):
                    return expanded
            return os.path.expanduser("~/.bash_profile")
        elif shell == "zsh":
            return os.path.expanduser("~/.zshrc")
        else:
            # Generic fallback
            return os.path.expanduser(f"~/.{shell}rc")
    
    # ==================== PACKAGE CLASSIFICATION ====================
    
    @lru_cache(maxsize=50)
    def _brew_list(self, kind: str) -> Set[str]:
        """
        Get installed Homebrew packages of a specific type.
        kind: "formula" or "cask"
        """
        try:
            result = subprocess.run(
                ["brew", "list", f"--{kind}"], 
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return set(result.stdout.split())
        except Exception as e:
            logger.warning(f"Could not list {kind} packages: {e}")
        return set()
    
    def classify_package(self, name: str) -> str:
        """
        Classify a package as 'tool', 'app', or 'unknown'.
        
        Returns:
            - "tool" if it's a Homebrew formula (command-line tool)
            - "app" if it's a Homebrew cask (GUI application)  
            - "unknown" if not found in Homebrew
        """
        # Remove version suffix for classification
        base_name = name.split('@')[0]
        
        if base_name in self._brew_list("formula"):
            return "tool"
        elif base_name in self._brew_list("cask"):
            return "app"
        else:
            return "unknown"
    
    def smart_package_resolution(self, name: str) -> tuple[str, str]:
        """
        Intelligently resolve package names by trying multiple variants.
        
        Returns:
            tuple: (resolved_name, package_type) or (original_name, "unknown")
        """
        base_name = name.split('@')[0].lower()
        
        # Try exact name first
        classification = self.classify_package(name)
        if classification != "unknown":
            return name, classification
            
        # Try common variants for popular apps
        variants_to_try = []
        
        # For apps that might have -client suffix incorrectly
        if base_name.endswith('-client'):
            variants_to_try.append(base_name[:-7])  # Remove -client
            
        # For development tools that might need community edition
        if base_name in ['intellij', 'pycharm', 'webstorm']:
            variants_to_try.extend([
                f"{base_name}-idea-ce",
                f"{base_name}-community", 
                f"{base_name}-ce"
            ])
            
        # For browsers and media apps
        if base_name in ['chrome', 'google-chrome']:
            variants_to_try.extend(['google-chrome', 'chrome'])
            
        # Try each variant
        for variant in variants_to_try:
            classification = self.classify_package(variant)
            if classification != "unknown":
                logger.info(f"Resolved '{name}' to '{variant}' ({classification})")
                return variant, classification
                
        return name, "unknown"
    
    def is_upgradable(self, tool_name: str) -> bool:
        """Check if a tool supports version switching."""
        base_name = tool_name.lower().split('@')[0]
        return base_name in self.UPGRADABLE_TOOLS
    
    def can_downgrade(self, formula: str, version: str) -> bool:
        """Check if a formula supports downgrading to a specific version."""
        try:
            result = subprocess.run(
                ["brew", "info", "--json=v2", formula], 
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                if data.get("formulae"):
                    formula_data = data["formulae"][0]
                    # Look for versioned aliases like "node@14"
                    aliases = formula_data.get("aliases", [])
                    return any(alias.endswith(f"@{version}") for alias in aliases)
        except Exception as e:
            logger.debug(f"Could not check downgrade capability for {formula}: {e}")
        return False
    
    # ==================== VERSION DETECTION ====================
    
    def _extract_version_from_output(self, output: str) -> str:
        """
        Extract version number from command output.
        Returns a normalized version string.
        """
        # Common version patterns
        patterns = [
            r'version "([^"]+)"',           # Java: openjdk version "21.0.8"
            r'v(\d+\.\d+(?:\.\d+)*)',      # Node: v20.1.0
            r'(\d+\.\d+(?:\.\d+)*)',       # Generic: 3.12.0
            r'version (\d+\.\d+(?:\.\d+)*)', # Docker: version 20.10.8
            r'Python (\d+\.\d+(?:\.\d+)*)', # Python: Python 3.13.5
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                version = match.group(1)
                try:
                    # Normalize version using packaging library
                    return str(parse_version(version))
                except Exception:
                    return version
        
        # If no pattern matches, return first line (cleaned up)
        first_line = output.split('\n')[0].strip()
        return first_line if first_line else "unknown"
    
    def _extract_version_tuple(self, output: str) -> Optional[Tuple[int, ...]]:
        """
        Extract version as tuple for comparison.
        Returns tuple like (3, 13, 5) or None if parsing fails.
        """
        version_str = self._extract_version_from_output(output)
        if version_str == "unknown":
            return None
            
        # Extract numeric parts
        numbers = re.findall(r'\d+', version_str)
        if numbers:
            try:
                return tuple(int(n) for n in numbers[:3])  # Take first 3 components
            except ValueError:
                pass
        return None
    
    def _get_python_version_commands(self, tool_name: str) -> List[List[str]]:
        """
        Get comprehensive list of Python commands to try, prioritizing system paths.
        """
        if tool_name.lower() not in ['python', 'python3', 'py']:
            return []
        
        commands = []
        
        # Add system-level Python commands first (bypass virtual environments)
        for path in self.SYSTEM_PYTHON_PATHS:
            commands.extend([
                [path, '--version'],
                [path, '-V'],
            ])
        
        # Add standard commands that might use virtual environment
        commands.extend([
            ['python3', '--version'],
            ['python3', '-V'],
            ['python', '--version'],
            ['python', '-V'],
            ['py', '--version'],
            ['py', '-V'],
        ])
        
        return commands
    
    def get_homebrew_package_version(self, package_name: str) -> str:
        """
        Get the installed version of a Homebrew package directly from brew list.
        This is more reliable for versioned packages like openjdk@17.
        """
        try:
            result = subprocess.run(
                ["brew", "list", "--versions", package_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                # Output format: "package_name version"
                parts = result.stdout.strip().split()
                if len(parts) >= 2:
                    return parts[1]  # Return the version part
        except Exception as e:
            logger.debug(f"Could not get Homebrew version for {package_name}: {e}")
        return "unknown"

    def check_active_version(self, tool_name: str) -> Dict:
        """
        Check what version of a tool is currently active in the PATH.
        For Python, implements smart logic to find the highest system version.
        """
        try:
            # Special handling for Python - try multiple versions and return the highest
            if tool_name.lower() in ['python', 'python3', 'py']:
                return self._check_python_version_smart(tool_name)
            
            # Standard version commands for common tools
            version_commands = {
                "java": ["java", "-version"],
                "node": ["node", "--version"],
                "npm": ["npm", "--version"],
                "docker": ["docker", "--version"],
                "git": ["git", "--version"],
                "go": ["go", "version"],
                "rust": ["rustc", "--version"],
                "ruby": ["ruby", "--version"],
                "php": ["php", "--version"],
            }
            
            # Get commands to try
            commands_to_try = []
            
            # Add known command if available
            if tool_name.lower() in version_commands:
                commands_to_try.append(version_commands[tool_name.lower()])
            
            # Add standard fallbacks
            commands_to_try.extend([
                [tool_name, "--version"],
                [tool_name, "-v"],
                [tool_name, "-version"],
                [tool_name, "version"],
            ])
            
            # Try each command
            for cmd in commands_to_try:
                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if result.returncode == 0:
                        output = result.stdout.strip() or result.stderr.strip()
                        if output:
                            version = self._extract_version_from_output(output)
                            return {
                                "found": True,
                                "version": version,
                                "raw_output": output,
                                "command_used": cmd
                            }
                except FileNotFoundError:
                    continue
                except Exception:
                    continue
            
            return {"found": False}
                
        except Exception as e:
            logger.debug(f"Could not check active version for {tool_name}: {e}")
            return {"found": False}
    
    def _check_python_version_smart(self, tool_name: str) -> Dict:
        """
        Smart Python version checking that tries multiple installations
        and returns the output from the highest version found.
        """
        commands_to_try = self._get_python_version_commands(tool_name)
        
        best_version = None
        best_output = None
        best_command = None
        
        for cmd in commands_to_try:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    output = result.stdout.strip() or result.stderr.strip()
                    if output:
                        version_tuple = self._extract_version_tuple(output)
                        if version_tuple:
                            # Compare with current best version
                            if best_version is None or version_tuple > best_version:
                                best_version = version_tuple
                                best_output = output
                                best_command = cmd
                        elif best_output is None:
                            # If we can't parse version, save as fallback
                            best_output = output
                            best_command = cmd
            except FileNotFoundError:
                continue
            except Exception:
                continue
        
        if best_output:
            version = self._extract_version_from_output(best_output)
            return {
                "found": True,
                "version": version,
                "raw_output": best_output,
                "command_used": best_command,
                "is_system_python": best_command and best_command[0] in self.SYSTEM_PYTHON_PATHS
            }
        
        return {"found": False}
    
    # ==================== SHELL CONFIGURATION ====================
    
    def append_to_shell_config(self, lines: List[str], comment: str = "Added by DevForge CLI Agent") -> bool:
        """
        Append lines to the appropriate shell configuration file.
        
        Args:
            lines: List of shell commands/exports to add
            comment: Comment to add before the lines
            
        Returns:
            True if successful, False otherwise
        """
        try:
            rc_file = self.get_rc_file()
            
            # Read existing content to avoid duplicates
            existing_content = ""
            if os.path.exists(rc_file):
                with open(rc_file, 'r') as f:
                    existing_content = f.read()
            
            # Check if our lines are already present
            lines_to_add = []
            for line in lines:
                if line.strip() and line.strip() not in existing_content:
                    lines_to_add.append(line)
            
            if not lines_to_add:
                logger.info("Shell configuration already up to date")
                return True
            
            # Append new lines
            with open(rc_file, 'a') as f:
                f.write(f"\n# {comment}\n")
                f.write('\n'.join(lines_to_add) + '\n')
            
            logger.info(f"Updated shell configuration: {rc_file}")
            return True
            
        except Exception as e:
            logger.error(f"Could not update shell configuration: {e}")
            return False
    
    # ==================== SECURITY & CONFIRMATION ====================
    
    def confirm_privileged_operation(self, operation: str, package: str) -> bool:
        """
        Ask user confirmation for operations that might require elevated privileges.
        In a CLI context, this would prompt the user. Here we return True for now.
        """
        # In a real implementation, this would use rich.Console or input()
        # For now, we'll assume consent (this should be overridden by the calling code)
        logger.info(f"Privileged operation requested: {operation} {package}")
        return True
    
    # ==================== CLEANUP ====================
    
    def cleanup_package_leftovers(self, package_name: str) -> None:
        """
        Clean up leftover files after package uninstallation.
        """
        cleanup_paths = [
            f"~/Library/Caches/{package_name}",
            f"~/Library/Application Support/{package_name}",
            f"/Library/Application Support/{package_name}",
            f"~/Library/Preferences/{package_name}*",
        ]
        
        cleaned = []
        for path_pattern in cleanup_paths:
            expanded = os.path.expanduser(path_pattern)
            
            # Handle glob patterns
            if '*' in expanded:
                import glob
                matching_paths = glob.glob(expanded)
                for path in matching_paths:
                    if os.path.exists(path):
                        try:
                            if os.path.isdir(path):
                                shutil.rmtree(path)
                            else:
                                os.remove(path)
                            cleaned.append(path)
                        except Exception as e:
                            logger.debug(f"Could not remove {path}: {e}")
            else:
                if os.path.exists(expanded):
                    try:
                        if os.path.isdir(expanded):
                            shutil.rmtree(expanded)
                        else:
                            os.remove(expanded)
                        cleaned.append(expanded)
                    except Exception as e:
                        logger.debug(f"Could not remove {expanded}: {e}")
        
        if cleaned:
            logger.info(f"Cleaned up leftover files for {package_name}: {cleaned}")
    
    # ==================== MAIN OPERATIONS ====================
    
    def check_version(self, tool_name: str) -> Dict:
        """
        Check what version of a tool is installed and active.
        This is the main entry point for version checking.
        """
        logger.info(f"Checking version for: {tool_name}")
        
        # Check active version first
        active_info = self.check_active_version(tool_name)
        
        if active_info.get("found", False):
            package_type = self.classify_package(tool_name)
            
            result = {
                "status": "success",
                "tool_name": tool_name,
                "version": active_info["version"],
                "raw_output": active_info["raw_output"],
                "package_type": package_type,
                "is_upgradable": self.is_upgradable(tool_name),
                "source": "active_in_path"
            }
            
            # Add special info for Python
            if tool_name.lower() in ['python', 'python3', 'py']:
                result.update({
                    "is_system_python": active_info.get("is_system_python", False),
                    "in_virtualenv": self.in_virtualenv(),
                    "system_python_version": self.get_system_python_version() if not active_info.get("is_system_python", False) else active_info["version"]
                })
            
            return result
        else:
            return {
                "status": "error",
                "tool_name": tool_name,
                "message": f"{tool_name} is not installed or not found in PATH"
            }
    
    def install_tool(self, tool_spec: str, force: bool = False) -> Dict:
        """
        Install a tool with proper version handling.
        
        Args:
            tool_spec: Tool specification like "python@3.13.5" or "docker"
            force: Whether to force reinstall if already present
            
        Returns:
            Dictionary with status, message, and details
        """
        # Parse tool specification
        if '@' in tool_spec:
            tool_name, version = tool_spec.split('@', 1)
        else:
            tool_name, version = tool_spec, "latest"
        
        logger.info(f"Installing {tool_name} version {version}")
        
        # Use smart package resolution
        resolved_name, package_type = self.smart_package_resolution(tool_name)
        
        if package_type == "unknown":
            return {
                "status": "error",
                "message": f"{tool_name} is not available via Homebrew. Try: brew search {tool_name}"
            }
        
        # Update tool_name to use resolved name
        tool_name = resolved_name
        
        # Validate version requirements
        if package_type == "tool" and version == "latest" and self.is_upgradable(tool_name):
            return {
                "status": "error",
                "message": f"Tools require an explicit version. Please specify: {tool_name}@<version>"
            }
        elif package_type == "app" and version != "latest":
            return {
                "status": "error", 
                "message": f"Applications only support 'latest' version. To change versions, uninstall and reinstall {tool_name}"
            }
        
        # Check if already installed
        if not force:
            current_version = self.check_version(tool_name)
            if current_version.get("status") == "success":
                if version == "latest" or current_version.get("version") == version:
                    return {
                        "status": "success",
                        "message": f"{tool_name} version {current_version.get('version')} is already installed",
                        "already_installed": True
                    }
        
        # Determine install command
        install_package = f"{tool_name}@{version}" if version != "latest" else tool_name
        
        try:
            if package_type == "app":
                cmd = ["brew", "install", "--cask", install_package]
            else:
                cmd = ["brew", "install", install_package]
            
            logger.info(f"Running: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes
            )
            
            if result.returncode == 0:
                # Clear cache after successful install to ensure fresh results
                self._brew_list.cache_clear()
                
                # Handle post-install configuration
                success_details = {
                    "status": "success",
                    "message": f"Successfully installed {tool_name} version {version}",
                    "package": install_package,
                    "package_type": package_type
                }
                
                # For command-line tools, might need PATH updates
                if package_type == "tool":
                    # Check if tool is now accessible
                    post_install_check = self.check_active_version(tool_name)
                    if post_install_check.get("found"):
                        success_details["installed_version"] = post_install_check["version"]
                    else:
                        # Might need shell restart
                        success_details["message"] += ". You may need to restart your terminal or run 'source ~/.zshrc'"
                
                return success_details
            else:
                error_output = result.stderr.strip() or result.stdout.strip()
                return {
                    "status": "error",
                    "message": f"Failed to install {tool_name}: {error_output}",
                    "error_details": error_output
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Installation failed: {str(e)}"
            }
    
    def upgrade_tool(self, tool_name: str) -> Dict:
        """
        Upgrade a tool to the latest version.
        """
        logger.info(f"Upgrading {tool_name}")
        
        package_type = self.classify_package(tool_name)
        
        if package_type == "unknown":
            return {
                "status": "error",
                "message": f"{tool_name} is not installed via Homebrew"
            }
        
        try:
            if package_type == "app":
                cmd = ["brew", "upgrade", "--cask", tool_name]
            else:
                cmd = ["brew", "upgrade", tool_name]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode == 0:
                # Clear cache after successful upgrade to ensure fresh results
                self._brew_list.cache_clear()
                
                # Check new version - for versioned packages, use Homebrew info
                if "@" in tool_name:
                    # For versioned packages like openjdk@17, get version from Homebrew
                    new_version = self.get_homebrew_package_version(tool_name)
                else:
                    # For regular packages, try to check active version
                    new_version_info = self.check_active_version(tool_name)
                    new_version = new_version_info.get("version", "unknown") if new_version_info.get("found") else "unknown"
                    
                    # Fallback to Homebrew if active version check fails
                    if new_version == "unknown":
                        new_version = self.get_homebrew_package_version(tool_name)

                return {
                    "status": "success",
                    "message": f"Successfully upgraded {tool_name} to version {new_version}",
                    "new_version": new_version
                }
            else:
                error_output = result.stderr.strip() or result.stdout.strip()
                # Check if it's already up to date
                if "already installed" in error_output.lower() or "nothing to upgrade" in error_output.lower():
                    # Get current version using Homebrew for versioned packages
                    if "@" in tool_name:
                        version = self.get_homebrew_package_version(tool_name)
                    else:
                        current_version = self.check_active_version(tool_name)
                        version = current_version.get("version", "unknown") if current_version.get("found") else "unknown"
                        if version == "unknown":
                            version = self.get_homebrew_package_version(tool_name)
                    
                    return {
                        "status": "success",
                        "message": f"{tool_name} is already up to date (version {version})",
                        "already_latest": True,
                        "new_version": version
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Failed to upgrade {tool_name}: {error_output}"
                    }
                    
        except Exception as e:
            return {
                "status": "error",
                "message": f"Upgrade failed: {str(e)}"
            }
    
    def uninstall_tool(self, tool_name: str, cleanup: bool = True) -> Dict:
        """
        Uninstall a tool and optionally clean up leftover files.
        """
        logger.info(f"Uninstalling {tool_name}")
        
        package_type = self.classify_package(tool_name)
        
        if package_type == "unknown":
            return {
                "status": "error",
                "message": f"{tool_name} is not installed via Homebrew"
            }
        
        try:
            if package_type == "app":
                cmd = ["brew", "uninstall", "--cask", tool_name]
            else:
                cmd = ["brew", "uninstall", tool_name]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                # Clear cache after successful uninstall to ensure fresh results
                self._brew_list.cache_clear()
                
                success_msg = f"Successfully uninstalled {tool_name}"
                
                # Clean up leftover files for GUI apps
                if cleanup and package_type == "app":
                    self.cleanup_package_leftovers(tool_name)
                    success_msg += " and cleaned up leftover files"
                
                return {
                    "status": "success",
                    "message": success_msg
                }
            else:
                error_output = result.stderr.strip() or result.stdout.strip()
                return {
                    "status": "error",
                    "message": f"Failed to uninstall {tool_name}: {error_output}"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Uninstall failed: {str(e)}"
            }


# ==================== CONVENIENCE FUNCTIONS ====================

# Global instance for backwards compatibility
_manager = None

def get_manager() -> MacToolManager:
    """Get a singleton instance of MacToolManager."""
    global _manager
    if _manager is None:
        _manager = MacToolManager()
    return _manager
