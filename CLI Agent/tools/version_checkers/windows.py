import subprocess
import re

def check_version(tool,version=None):
    try:
        # subprocess.run with list args handles spaces correctly
        cmd = ["winget", "list", tool]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            lines = result.stdout.splitlines()
            for line in lines:
                # Match line containing tool name (case-insensitive)
                if tool.lower() in line.lower():
                    # Regex to match version pattern like 2.5.10921.0 or 2.2524.4.0
                    match = re.search(r'\b(\d+(?:\.\d+)+)\b', line)
                    if match:
                        return {
                            "status": "success",
                            "message": f"{tool} version: {match.group(1)} (Windows/winget)"
                        }
            return {
                "status": "success",
                "message": f"{tool} not found or version not detected (Windows/winget)"
            }
        else:
            return {
                "status": "error",
                "message": result.stderr.strip() or result.stdout.strip()
            }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
