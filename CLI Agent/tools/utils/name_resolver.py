def resolve_tool_name(raw_name: str, os_type: str, version: str = "latest") -> dict:
    """
    Maps user-friendly tool names and versions to actual package names for each OS/distro.

    Returns a dict:
    {
      "name": resolved_tool_name,
      "fallback": fallback_message or None
    }
    """
    normalized = raw_name.lower()
    fallback_message = None

    # Linux mapping logic with version-specific handling
    if os_type.lower() == "linux":
        if normalized == "java":
            if version.startswith("11"):
                resolved = "openjdk-11-jdk"
            elif version.startswith("17"):
                resolved = "openjdk-17-jdk"
            elif version.startswith("21"):
                resolved = "openjdk-21-jdk"
            elif version.startswith("24"):
                resolved = "openjdk-24-jdk"
            else:
                resolved = "default-jdk"
                if version != "latest":
                    fallback_message = f"Version '{version}' not specifically supported for Java on Linux. Falling back to 'default-jdk'."
            return {"name": resolved, "fallback": fallback_message}

        if normalized == "python":
            if version.startswith("3.9"):
                resolved = "python3.9"
            elif version.startswith("3.10"):
                resolved = "python3.10"
            elif version.startswith("3.11"):
                resolved = "python3.11"
            elif version.startswith("3.12"):
                resolved = "python3.12"
            else:
                resolved = "python3"
                if version != "latest":
                    fallback_message = f"Version '{version}' not specifically supported for Python on Linux. Falling back to 'python3'."
            return {"name": resolved, "fallback": fallback_message}

        name_map = {
            "node": "nodejs",
            "nodejs": "nodejs",
            "vscode": "code",
            "nvim": "neovim",
            "docker": "docker.io",
        }
        return {"name": name_map.get(normalized, raw_name), "fallback": None}

    # macOS mapping with brew-style version suffixes
    if os_type.lower() == "darwin":
        if normalized == "python":
            if version != "latest" and version.startswith("3."):
                resolved = f"python@{version}"
            else:
                resolved = "python@3.11"  # fallback default
                if version != "latest":
                    fallback_message = f"Version '{version}' not specifically supported for Python on macOS. Falling back to 'python@3.11'."
            return {"name": resolved, "fallback": fallback_message}

        if normalized == "java":
            resolved = "openjdk"
            # We can add more version handling here later if needed
            return {"name": resolved, "fallback": None}

        name_map = {
            "node": "node",
            "nodejs": "node",
            "vscode": "visual-studio-code",
            "nvim": "neovim",
            "docker": "docker",
        }
        return {"name": name_map.get(normalized, raw_name), "fallback": None}

    # Windows mapping (winget identifiers are often namespaced or friendly names)
    if os_type.lower() == "windows":
        name_map = {
            "java": "OpenJDK",
            "python": "Python",
            "node": "Node.js",
            "nodejs": "Node.js",
            "vscode": "Visual Studio Code",
            "nvim": "Neovim",
            "docker": "Docker Desktop",
        }
        return {"name": name_map.get(normalized, raw_name), "fallback": None}

    # If OS not recognized or no mapping found, return raw name without fallback
    return {"name": raw_name, "fallback": None}
