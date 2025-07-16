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
        if normalized == "python":
            if context == "version_check":
                return {"name": "python3", "fallback": None, "classic_snap": False}
            if version != "latest":
                return {"name": f"python@{version}", "fallback": None, "classic_snap": False}
            return {"name": "python@3.11", "fallback": "Falling back to python@3.11", "classic_snap": False}

        elif normalized == "java":
            if context == "version_check":
                return {"name": "java", "fallback": None, "classic_snap": False}
            return {"name": "openjdk", "fallback": None, "classic_snap": False}

        name_map = {
            "node": "node",
            "nodejs": "node",
            "vscode": "visual-studio-code",
            "nvim": "neovim",
            "docker": "docker",
            "intellij": "intellij-idea-ce",
            "pycharm": "pycharm-ce",
            "eclipse": "eclipse-java"
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
            "eclipse": "eclipse.exe" if context == "version_check" else "Eclipse IDE"
        }
        resolved_name = name_map.get(normalized, raw_name)
        return {"name": resolved_name, "fallback": None, "classic_snap": False}

    # Fallback for unknown OS/tool
    return {"name": raw_name, "fallback": None, "classic_snap": False}
