def format_uninstaller_output(raw: str) -> str:
    """Clean up and summarize uninstaller output for user-friendly display."""
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
        if (
            l.startswith("Found ") or
            l.startswith("Starting package uninstall") or
            l.startswith("Successfully uninstalled") or
            l.startswith("Uninstalled ") or
            "no package found" in l.lower() or
            "no installed package found" in l.lower() or
            "no available uninstall" in l.lower() or
            "no installed package matching input criteria" in l.lower()
        ):
            keep.append(l)
        elif "MB /" in l:
            keep.append(l)
    # If nothing found, try to find any error or info line
    if not keep and lines:
        for l in lines:
            if "error" in l.lower() or "not found" in l.lower():
                keep.append(l.strip())
        # If still nothing, fallback to first and last non-empty line
        if not keep:
            filtered = [x for x in lines if x.strip()]
            if filtered:
                keep = [filtered[0].strip(), filtered[-1].strip()]
    return "\n".join(keep)
import subprocess

def uninstall_windows_tool(tool):
    try:
        cmd = ["winget", "uninstall", tool, "--silent", "--accept-source-agreements"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout + "\n" + result.stderr
        if result.returncode == 0:
            formatted = format_uninstaller_output(output)
            return {"status": "success", "message": formatted or f"Uninstalled {tool}"}
        else:
            return {"status": "error", "message": format_uninstaller_output(output) or output.strip()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

