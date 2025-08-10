def resolve_tool_name(raw_name: str, os_type: str, version: str = "latest", context: str = "install") -> dict:
    """
    Map a user-provided tool name to an OS-appropriate package/executable.
    context: 'install' or 'version_check'
    """
    normalized = (raw_name or "").strip().lower()
    os_type = os_type.lower()
    fallback = None

    # Snaps that need classic confinement (UI IDEs etc.)
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

    # SDKMAN candidates on Linux/mac
    sdk_candidates_map = {
        "java": "java",
        "maven": "maven",
        "gradle": "gradle",
        "kotlin": "kotlin",
        "scala": "scala",
        "groovy": "groovy",
        "sbt": "sbt",
        "ant": "ant",
        "micronaut": "micronaut",
        "springboot": "springboot",
        "visualvm": "visualvm",
    }

    # Preferred apt package names (Linux)
    apt_name_map = {
        "git": "git",
        "curl": "curl",
        "zip": "zip",
        "unzip": "unzip",
        "build-essential": "build-essential",
        "gcc": "gcc",
        "g++": "g++",
        "make": "make",
        "cmake": "cmake",
        "python": "python3",
        "python3": "python3",
        "pip": "python3-pip",
        "python3-pip": "python3-pip",
        "node": "nodejs",
        "nodejs": "nodejs",
        "npm": "npm",
        "yarn": "yarnpkg",
        "docker": "docker.io",
        "docker.io": "docker.io",
        "neovim": "neovim",
        "nvim": "neovim",
    }

    # Preferred snap names (Linux)
    snap_name_map = {
        "vscode": "code",
        "code": "code",
        "intellij": "intellij-idea-community",
        "intellij-idea-community": "intellij-idea-community",
        "pycharm": "pycharm-community",
        "pycharm-community": "pycharm-community",
        "pycharm-professional": "pycharm-professional",
        "android-studio": "android-studio",
        "goland": "goland",
        "clion": "clion",
        "postman": "postman",
        "dbeaver": "dbeaver-ce",
        "dbeaver-ce": "dbeaver-ce",
    }

    if os_type == "linux":
        # Special-case Java (SDKMAN preference for checks)
        if normalized == "java":
            # Avoid default-jdk in version checks
            if context in ("version_check", "status"):
                return {
                    "name": "java",
                    "fallback": None,
                    "classic_snap": False,
                    "manager": None,          # no manager for checks
                    "sdk_candidate": "java",
                    "apt_name": None,         # skip apt for checks
                    "snap_name": "java",
                }
            # Versioned Java via apt (e.g., openjdk-17-jdk)
            if version and version.strip() != "latest":
                apt_pkg = f"openjdk-{version}-jdk"
                return {
                    "name": "java",
                    "fallback": None,
                    "classic_snap": False,
                    "manager": "apt",
                    "sdk_candidate": "java",
                    "apt_name": apt_pkg,
                    "snap_name": "java",
                }
            # Latest: prefer SDKMAN, keep apt as install fallback
            return {
                "name": "java",
                "fallback": None,
                "classic_snap": False,
                "manager": "sdkman",
                "sdk_candidate": "java",
                "apt_name": "default-jdk",  # install fallback
                "snap_name": "java",
            }

        # Python nuance: python -> python3 on Linux
        elif normalized == "python":
            if context == "version_check":
                return {"name": "python3", "fallback": None, "classic_snap": False}
            else:
                if version != "latest":
                    package = f"python{version}" if version.startswith("3.") else f"python{version}"
                    return {"name": package, "fallback": None, "classic_snap": False}
                return {"name": "python3", "fallback": None, "classic_snap": False}

        # Simple remaps for common tools
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

        # Base resolved name
        resolved_name = name_map.get(normalized, raw_name)

        # Choose manager: SDKMAN > snap (GUI/classic) > apt
        manager = None
        sdk_candidate = sdk_candidates_map.get(normalized)
        if sdk_candidate:
            manager = "sdkman"
        elif normalized in snap_name_map or resolved_name in classic_snap_packages:
            manager = "snap"
        else:
            manager = "apt"

        return {
            "name": resolved_name,
            "fallback": None,
            "classic_snap": resolved_name in classic_snap_packages,
            "manager": manager,
            "sdk_candidate": sdk_candidate,
            "apt_name": apt_name_map.get(normalized, apt_name_map.get(resolved_name, resolved_name)),
            "snap_name": snap_name_map.get(normalized, snap_name_map.get(resolved_name, resolved_name)),
        }

    elif os_type == "darwin":
        # macOS Homebrew mappings
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
        
        # openjdk-XX-jdk -> openjdk@XX
        elif normalized.startswith("openjdk-") and normalized.endswith("-jdk"):
            try:
                version_part = normalized[8:-4]  # strip "openjdk-" and "-jdk"
                if version_part.isdigit():
                    return {"name": f"openjdk@{version_part}", "fallback": None, "classic_snap": False}
            except:
                pass
            return {"name": "openjdk", "fallback": None, "classic_snap": False}

        # Other common mappings to brew casks/formulae
        name_map = {
            "node": "node",
            "nodejs": "node", 
            "vscode": "visual-studio-code",
            "code": "visual-studio-code",
            "nvim": "neovim",
            "neovim": "neovim",
            "docker": "docker",
            "docker.io": "docker",
            "go": "go",
            "golang": "go",
            "intellij": "intellij-idea-ce",
            "intellij-idea-community": "intellij-idea-ce",
            "pycharm": "pycharm-ce", 
            "pycharm-community": "pycharm-ce",
            "eclipse": "eclipse-java",
            "spotify": "spotify",
            "spotify-client": "spotify",
            "minikube": "minikube"
        }

        resolved_name = name_map.get(normalized, raw_name)

        if context == "version_check":
            # For checks, return the executable/binary name
            return {"name": resolved_name, "fallback": None, "classic_snap": False}

        return {"name": resolved_name, "fallback": None, "classic_snap": False}

    elif os_type == "windows":
        # Winget-friendly names vs executable names for version checks
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
            # Slack (Linux-style names mapped for Windows installs)
            "slack": "Slack",
            "slack-desktop": "Slack",
            # Generic Java name handling for winget search
            "default-jdk": "OpenJDK",
            "openjdk": "OpenJDK",
            "java-jdk": "OpenJDK",
            "jdk": "JDK" if context != "version_check" else "java"
        }

        # Map Linux-style 'openjdk-17-jdk' to a generic OpenJDK search term
        if normalized.startswith("openjdk-") and normalized.endswith("-jdk") and context != "version_check":
            return {"name": "OpenJDK", "fallback": None, "classic_snap": False}

        resolved_name = name_map.get(normalized, raw_name)
        return {"name": resolved_name, "fallback": None, "classic_snap": False}

    # Unknown OS/tool: return as-is
    return {"name": raw_name, "fallback": None, "classic_snap": False}
