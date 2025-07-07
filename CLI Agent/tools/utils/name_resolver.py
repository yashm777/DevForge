def resolve_tool_name(raw_name: str, os_type: str, version: str = "latest") -> dict:
    """
    Dynamically resolve the actual package name from user input tool name + version.

    Returns:
        dict: {
            "name": resolved_package_name,
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
            if version != "latest":
                package = f"openjdk-{version}-jdk"
                return {"name": package, "fallback": None, "classic_snap": False}
            return {"name": "default-jdk", "fallback": None, "classic_snap": False}

        elif normalized == "python":
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
        return {
            "name": resolved_name,
            "fallback": None,
            "classic_snap": resolved_name in classic_snap_packages
        }

    elif os_type == "darwin":
        if normalized == "python":
            if version != "latest":
                return {"name": f"python@{version}", "fallback": None, "classic_snap": False}
            return {"name": "python@3.11", "fallback": "Falling back to python@3.11", "classic_snap": False}

        elif normalized == "java":
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
        return {"name": resolved_name, "fallback": None, "classic_snap": False}

    elif os_type == "windows":
        name_map = {
            "java": "OpenJDK",
            "python": "Python",
            "node": "Node.js",
            "nodejs": "Node.js",
            "vscode": "Visual Studio Code",
            "nvim": "Neovim",
            "docker": "Docker Desktop",
            "intellij": "IntelliJ IDEA Community Edition",
            "pycharm": "PyCharm Community Edition",
            "eclipse": "Eclipse IDE"
        }
        resolved_name = name_map.get(normalized, raw_name)
        return {"name": resolved_name, "fallback": None, "classic_snap": False}

    # Fallback for unknown OS/tool
    return {"name": raw_name, "fallback": None, "classic_snap": False}
