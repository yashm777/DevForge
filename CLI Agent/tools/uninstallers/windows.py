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
            l.startswith("Uninstalled ")
        ):
            keep.append(l)
        elif "MB /" in l:
            keep.append(l)
    if not keep and lines:
        keep = [lines[0], lines[-1]]
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

