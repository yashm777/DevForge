def format_installer_output(raw: str) -> str:
    """Clean up and summarize installer output for user-friendly display."""
    # Only keep lines with key status messages, filter out progress bars and symbol-only lines
    import re
    lines = raw.splitlines()
    keep = []
    for line in lines:
        l = line.strip()
        if not l:
            continue
        # Filter out lines that are mostly symbols (progress bars)
        if re.fullmatch(r"[-\\/|]+", l):
            continue
        if re.fullmatch(r"[â–ˆ]+.*", l):
            continue
        # Keep lines with these keywords
        if (
            l.startswith("Found ") or
            l.startswith("Downloading ") or
            l.startswith("Successfully installed") or
            l.startswith("Successfully verified installer hash") or
            l.startswith("Starting package install") or
            l.startswith("This application is licensed") or
            l.startswith("Microsoft is not responsible") or
            l.startswith("Version ") or
            l.startswith("Install") or
            l.startswith("Installed ")
        ):
            keep.append(l)
        # Also keep lines with MB progress for download
        elif "MB /" in l:
            keep.append(l)
    # If nothing found, fallback to first and last lines
    if not keep and lines:
        keep = [lines[0], lines[-1]]
    return "\n".join(keep)
import subprocess
import re

def install_windows_tool(tool, version="latest"):
    # First, try to search for the tool to see if there are multiple matches
    search_cmd = ["winget", "search", tool]
    try:
        search_result = subprocess.run(search_cmd, capture_output=True, text=True)
        if search_result.returncode == 0:
            # Parse the search results to see if there are multiple matches
            lines = search_result.stdout.strip().split('\n')
            if len(lines) > 2:  # More than header + one result
                # Check for moniker matches (like "Moniker: docker")
                moniker_match = None
                for line in lines:
                    if f"Moniker: {tool.lower()}" in line.lower():
                        # Extract the ID from the line
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if "." in part and part.lower() not in ["version", "match", "tag:", "moniker:"]:
                                moniker_match = part
                                break
                        if moniker_match:
                            return install_windows_tool_by_id(moniker_match, version)
                
                # Extract package information from winget search output
                options = []
                for line in lines[2:]:  # Skip header lines
                    if line.strip():
                        # More robust parsing of the winget output
                        # First find the name (which might contain spaces)
                        name_end_pos = 0
                        parts = line.split()
                        if len(parts) >= 3:
                            # Try to identify the package ID which often contains a period
                            id_val = None
                            for part in parts:
                                if "." in part and not part.endswith(".") and not part.startswith("."):
                                    id_val = part
                                    break
                            
                            # If we couldn't find an ID with a period, use a simple approach
                            if id_val is None:
                                name = parts[0]
                                id_val = parts[1]
                                source = parts[2] if len(parts) > 2 else "winget"
                            else:
                                # If we found an ID, assume the name is everything before it
                                id_pos = line.find(id_val)
                                name = line[:id_pos].strip()
                                # And source is after the ID and version
                                source_parts = line[id_pos + len(id_val):].strip().split()
                                source = source_parts[-1] if source_parts else "winget"
                            
                            options.append({
                                "name": name,
                                "id": id_val,
                                "source": source
                            })
                
                # Check for exact name matches
                exact_matches = []
                for opt in options:
                    if opt["name"].lower() == tool.lower():
                        exact_matches.append(opt)
                
                if len(exact_matches) == 1:
                    # Found a single exact match by name
                    return install_windows_tool_by_id(exact_matches[0]["id"], version)
                
                if len(options) > 1:
                    return {
                        "status": "ambiguous",
                        "message": "Multiple packages found matching input criteria. Please refine the input.",
                        "options": options
                    }
    
    
    except Exception as e:
        print(f"Error searching for package: {str(e)}")
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
            return {"status": "success", "message": f"Installed {tool}"}
        else:
            # Check if error is due to multiple packages found
            if "Multiple packages found matching input criteria" in output:
                # Try running the search again to get the options
                search_result = subprocess.run(["winget", "search", tool], capture_output=True, text=True)
                if search_result.returncode == 0:
                    lines = search_result.stdout.strip().split('\n')
                    options = []
                    
                    # Parse each line to extract package information
                    for line in lines[2:]:  # Skip header lines
                        if not line.strip():
                            continue
                            
                        parts = line.split()
                        if len(parts) < 3:
                            continue
                            
                        # Try to find the package ID (which usually contains a period)
                        id_val = None
                        for part in parts:
                            if "." in part and not part.endswith(".") and not part.startswith("."):
                                id_val = part
                                break
                        
                        if id_val:
                            id_pos = line.find(id_val)
                            name = line[:id_pos].strip()
                            
                            options.append({
                                "name": name,
                                "id": id_val,
                                "source": parts[-1] if len(parts) > 2 else "winget"
                            })
                    
                    return {
                        "status": "ambiguous",
                        "message": "Multiple packages found matching input criteria. Please refine the input.",
                        "options": options
                    }
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
            return {"status": "success", "message": f"Installed {package_id}"}
        else:
            # Check if error is due to multiple packages found
            if "Multiple packages found matching input criteria" in output:
                # Try to be more specific with the ID
                exact_cmd = ["winget", "install", "--exact", "--id", package_id,
                            "--silent", "--accept-source-agreements", "--accept-package-agreements"]
                if version != "latest":
                    exact_cmd += ["--version", version]
                
                exact_result = subprocess.run(exact_cmd, capture_output=True, text=True)
                exact_output = exact_result.stdout + "\n" + exact_result.stderr
                
                if exact_result.returncode == 0:
                    return {"status": "success", "message": exact_result.stdout.strip() or f"Installed {package_id}"}
                
                # If exact match fails, search for options
                search_result = subprocess.run(["winget", "search", package_id], capture_output=True, text=True)
                if search_result.returncode == 0:
                    lines = search_result.stdout.strip().split('\n')
                    options = []
                    
                    # Parse each line to extract package information
                    for line in lines[2:]:  # Skip header lines
                        if not line.strip():
                            continue
                            
                        parts = line.split()
                        if len(parts) < 3:
                            continue
                            
                        # Try to find the package ID (which usually contains a period)
                        id_val = None
                        for part in parts:
                            if "." in part and not part.endswith(".") and not part.startswith("."):
                                id_val = part
                                break
                        
                        if id_val:
                            id_pos = line.find(id_val)
                            name = line[:id_pos].strip()
                            
                            options.append({
                                "name": name,
                                "id": id_val,
                                "source": parts[-1] if len(parts) > 2 else "winget"
                            })
                    
                    return {
                        "status": "ambiguous",
                        "message": "Multiple packages found matching input criteria. Please refine the input.",
                        "options": options
                    }
            return {"status": "error", "message": output.strip()}
    except Exception as e:
        return {"status": "error", "message": str(e)}
