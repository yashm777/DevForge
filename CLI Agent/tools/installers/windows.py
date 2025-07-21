import subprocess
import re

def install_windows_tool(tool, version="latest"):
    # Map common aliases to known winget package IDs for Java
    java_aliases = {
        "java": "EclipseAdoptium.Temurin.17.JDK",
        "jdk": "EclipseAdoptium.Temurin.17.JDK",
        "openjdk": "EclipseAdoptium.Temurin.17.JDK"
    }
    tool_lower = tool.strip().lower()
    if tool_lower in java_aliases:
        tool = java_aliases[tool_lower]
    # First, try to search for the tool to see if there are multiple matches
    search_cmd = ["winget", "search", tool]
    try:
        search_result = subprocess.run(search_cmd, capture_output=True, text=True)
        if search_result.returncode == 0:
            # Parse the search results to see if there are multiple matches
            lines = search_result.stdout.strip().split('\n')
            if len(lines) > 2:  # More than header + one result
                # Extract package information from winget search output
                options = []
                for line in lines[2:]:  # Skip header lines
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 3:
                            name = parts[0]
                            id_match = re.search(r'([A-Za-z0-9.-]+)', parts[1])
                            id_val = id_match.group(1) if id_match else parts[1]
                            source = parts[2] if len(parts) > 2 else "winget"
                            options.append({
                                "name": name,
                                "id": id_val,
                                "source": source
                            })
                
                if len(options) > 1:
                    return {
                        "status": "ambiguous",
                        "message": "Multiple packages found matching input criteria. Please refine the input.",
                        "options": options
                    }
    
    except Exception:
        pass  # Continue with installation if search fails
    
    # Proceed with installation using the original tool name
    cmd = [
        "winget", "install", tool,
        "--silent", "--accept-source-agreements", "--accept-package-agreements"
    ]
    if version != "latest":
        cmd += ["--version", version]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout + "\n" + result.stderr
        if result.returncode == 0:
            return {"status": "success", "message": result.stdout.strip() or f"Installed {tool}"}
        else:
            return {"status": "error", "message": output.strip()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def install_windows_tool_by_id(package_id, version="latest"):
    """Install a specific package by its ID"""
    cmd = [
        "winget", "install", package_id,
        "--silent", "--accept-source-agreements", "--accept-package-agreements"
    ]
    if version != "latest":
        cmd += ["--version", version]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout + "\n" + result.stderr
        if result.returncode == 0:
            return {"status": "success", "message": result.stdout.strip() or f"Installed {package_id}"}
        else:
            return {"status": "error", "message": output.strip()}
    except Exception as e:
        return {"status": "error", "message": str(e)}
