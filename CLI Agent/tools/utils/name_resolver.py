def resolve_tool_name(raw_name: str, os_type: str, version: str = "latest") -> dict:
    """
    Dynamically resolve the actual package name from user input tool name + version.

    Returns:
        dict: {
            "name": resolved_package_name,
            "fallback": fallback_message (or None)
        }
    """
    normalized = raw_name.lower()
    os_type = os_type.lower()
    fallback = None

    if os_type == "linux":
        if normalized == "java":
            if version != "latest":
                package = f"openjdk-{version}-jdk"
                return {"name": package, "fallback": None}
            return {"name": "default-jdk", "fallback": None}

        elif normalized == "python":
            if version != "latest":
                package = f"python{version}" if version.startswith("3.") else f"python{version}"
                return {"name": package, "fallback": None}
            return {"name": "python3", "fallback": None}

        name_map = {
            "node": "nodejs",
            "nodejs": "nodejs",
            "vscode": "code",
            "nvim": "neovim",
            "docker": "docker.io",                  
            "intellij": "intellij-idea-community",  # Snap/Flatpak or JetBrains repo
            "pycharm": "pycharm-community",         # Snap/Flatpak
            "eclipse": "eclipse"
        }
        return {"name": name_map.get(normalized, raw_name), "fallback": None}

    elif os_type == "darwin":
        if normalized == "python":
            if version != "latest":
                return {"name": f"python@{version}", "fallback": None}
            return {"name": "python@3.11", "fallback": "Falling back to python@3.11"}

        elif normalized == "java":
            return {"name": "openjdk", "fallback": None}

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
        return {"name": name_map.get(normalized, raw_name), "fallback": None}

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
        return {"name": name_map.get(normalized, raw_name), "fallback": None}

    return {"name": raw_name, "fallback": None}
