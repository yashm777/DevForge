def resolve_tool_name(raw_name: str, os_type: str, version: str = "latest", context: str = "install") -> dict:
    """
    Dynamically resolve the actual package name or executable name from user input tool name + version,
    depending on context ('install' or 'version_check').

    Returns:
        dict: {
            "name": resolved_name,
            "fallback": fallback_message (or None),
            "classic_snap": bool
        }
    """
    normalized = raw_name.lower()
    os_type = os_type.lower()
    fallback = None

    classic_snap_packages = {
        "intellij-idea-community",
        "pycharm-community",
        "pycharm-professional",
        "android-studio",
        "goland",
        "clion",
        "code",  # vscode snap
        "vscode"
    }

    if os_type == "linux":
        if normalized == "java":
            if context == "version_check":
                # For version checking, return the executable name
                return {"name": "java", "fallback": None, "classic_snap": False}
            else:
                # For install/uninstall context
                if version.strip() != "latest":
                    package = f"openjdk-{version}-jdk"
                    return {"name": package, "fallback": None, "classic_snap": False}
                return {"name": "default-jdk", "fallback": None, "classic_snap": False}

        elif normalized == "python":
            if context == "version_check":
                return {"name": "python3", "fallback": None, "classic_snap": False}
            else:
                if version != "latest":
                    package = f"python{version}" if version.startswith("3.") else f"python{version}"
                    return {"name": package, "fallback": None, "classic_snap": False}
                return {"name": "python3", "fallback": None, "classic_snap": False}

        name_map = {
            "node": "nodejs",
            "nodejs": "nodejs",
            "vscode": "code",
            "nvim": "neovim",
            "docker": "docker.io",
            "intellij": "intellij-idea-community",
            "pycharm": "pycharm-community",
            "eclipse": "eclipse"
        }

        resolved_name = name_map.get(normalized, raw_name)

        if context == "version_check":
            # Return executable name for version check where applicable
            # For example, 'code' is executable for vscode snap
            if normalized == "vscode":
                return {"name": "code", "fallback": None, "classic_snap": False}
            return {"name": resolved_name, "fallback": None, "classic_snap": resolved_name in classic_snap_packages}

        return {
            "name": resolved_name,
            "fallback": None,
            "classic_snap": resolved_name in classic_snap_packages
        }

    elif os_type == "darwin":
        if normalized == "python" or normalized == "python3":
            if context == "version_check":
                return {"name": "python3", "fallback": None, "classic_snap": False}
            if version != "latest":
                return {"name": f"python@{version}", "fallback": None, "classic_snap": False}
            return {"name": "python@3.11", "fallback": "Falling back to python@3.11", "classic_snap": False}

        elif normalized == "java" or normalized == "default-jdk":
            if context == "version_check":
                return {"name": "java", "fallback": None, "classic_snap": False}
            return {"name": "openjdk", "fallback": None, "classic_snap": False}
        
        # Handle versioned Java packages (openjdk-XX-jdk -> openjdk@XX)
        elif normalized.startswith("openjdk-") and normalized.endswith("-jdk"):
            # Extract version number from openjdk-17-jdk format
            try:
                version_part = normalized[8:-4]  # Remove "openjdk-" and "-jdk"
                if version_part.isdigit():
                    return {"name": f"openjdk@{version_part}", "fallback": None, "classic_snap": False}
            except:
                pass
            # Fallback to default openjdk if parsing fails
            return {"name": "openjdk", "fallback": None, "classic_snap": False}

        name_map = {
            "node": "node",
            "nodejs": "node", 
            "vscode": "visual-studio-code",
            "code": "visual-studio-code",  # Handle both vscode -> code -> visual-studio-code
            "nvim": "neovim",
            "neovim": "neovim",
            "docker": "docker",
            "docker.io": "docker",  # Map Linux docker.io to Mac docker
            "go": "go",  # Handle LLM's go -> golang transformation
            "golang": "go",  # Map LLM's golang back to go executable
            "intellij": "intellij-idea-ce",
            "intellij-idea-community": "intellij-idea-ce",  # Map Linux name to Mac name
            "pycharm": "pycharm-ce", 
            "pycharm-community": "pycharm-ce",  # Map Linux name to Mac name
            "eclipse": "eclipse-java",
            "spotify": "spotify",  # Ensure spotify maps to correct cask name
            "spotify-client": "spotify"  # Fix LLM's incorrect spotify-client mapping
        }

        resolved_name = name_map.get(normalized, raw_name)

        if context == "version_check":
            # Return executable names for version check context if different
            # (usually the same)
            return {"name": resolved_name, "fallback": None, "classic_snap": False}

        return {"name": resolved_name, "fallback": None, "classic_snap": False}

    elif os_type == "windows":
        name_map = {
            "java": "java" if context == "version_check" else "OpenJDK",
            "python": "python" if context == "version_check" else "Python",
            "node": "node" if context == "version_check" else "Node.js",
            "nodejs": "node" if context == "version_check" else "Node.js",
            "vscode": "code" if context == "version_check" else "Visual Studio Code",
            "nvim": "nvim" if context == "version_check" else "Neovim",
            "docker": "docker" if context == "version_check" else "Docker Desktop",
            "intellij": "idea64.exe" if context == "version_check" else "IntelliJ IDEA Community Edition",
            "pycharm": "pycharm64.exe" if context == "version_check" else "PyCharm Community Edition",
            "eclipse": "eclipse.exe" if context == "version_check" else "Eclipse IDE",
            # Slack mappings (handle Linux-style name on Windows)
            "slack": "Slack",
            "slack-desktop": "Slack",
            # Handle Linux-style Java names generically for Windows winget search
            "default-jdk": "OpenJDK",
            "openjdk": "OpenJDK",
            "java-jdk": "OpenJDK",
            "jdk": "JDK" if context != "version_check" else "java"
        }

        # Handle versioned Linux names like 'openjdk-17-jdk' by mapping to a generic search term
        if normalized.startswith("openjdk-") and normalized.endswith("-jdk") and context != "version_check":
            return {"name": "OpenJDK", "fallback": None, "classic_snap": False}
        }
        resolved_name = name_map.get(normalized, raw_name)
        return {"name": resolved_name, "fallback": None, "classic_snap": False}

    # Fallback for unknown OS/tool
    return {"name": raw_name, "fallback": None, "classic_snap": False}
