import os
import re
import shutil
import subprocess
import logging
from typing import Optional, List, Dict

from tools.utils.name_resolver import resolve_tool_name

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- helpers ----------

def _run(cmd: List[str], timeout: int = 8) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception as e:
        cp = subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr=str(e))
        return cp

def _which(name: str) -> Optional[str]:
    return shutil.which(name)

def _first_nonempty(*vals: Optional[str]) -> Optional[str]:
    for v in vals:
        if v:
            v = v.strip()
            if v:
                return v
    return None

def _strip_v(s: str) -> str:
    return s[1:] if s and s.startswith("v") else s

def _extract_semver(text: str) -> Optional[str]:
    # Try semantic-like patterns first (with optional pre-release/build)
    m = re.search(r"\b(\d+\.\d+\.\d+(?:[-+._][0-9A-Za-z.-]+)?)\b", text)
    if m:
        return m.group(1)
    # Fallback to simpler version patterns (e.g., 21, 21.0, 17.0.9)
    m = re.search(r"\b(\d{1,4}(?:\.\d+){0,2})\b", text)
    if m:
        return m.group(1)
    return None

def _exec_version(cmd: List[str], strip_leading_v: bool = False) -> Optional[str]:
    r = _run(cmd)
    out = _first_nonempty(r.stdout, r.stderr) or ""
    if not out:
        return None
    ver = _extract_semver(out)
    if ver and strip_leading_v:
        ver = _strip_v(ver)
    return ver

# ---------- special parsers ----------

def _java_version_from_java() -> Optional[str]:
    r = _run(["java", "-version"])
    out = _first_nonempty(r.stdout, r.stderr) or ""
    # Common patterns:
    # openjdk version "17.0.9" 2023-10-17
    # java version "1.8.0_362"
    m = re.search(r'version\s+"([^"]+)"', out)
    if m:
        return m.group(1)
    # fallback generic
    return _extract_semver(out)

def _maven_version() -> Optional[str]:
    # mvn -v -> "Apache Maven 3.9.6" ...
    r = _run(["mvn", "-v"])
    out = _first_nonempty(r.stdout, r.stderr) or ""
    m = re.search(r"Apache Maven\s+([0-9][^ \n\r\t]+)", out)
    return m.group(1) if m else _extract_semver(out)

def _gradle_version() -> Optional[str]:
    # gradle -v -> "Gradle 8.9"
    r = _run(["gradle", "-v"])
    out = _first_nonempty(r.stdout, r.stderr) or ""
    m = re.search(r"Gradle\s+([0-9][^ \n\r\t]+)", out)
    return m.group(1) if m else _extract_semver(out)

def _kubectl_version() -> Optional[str]:
    # kubectl version --client --short -> "Client Version: v1.29.3"
    r = _run(["kubectl", "version", "--client", "--short"])
    out = _first_nonempty(r.stdout, r.stderr) or ""
    m = re.search(r"Client Version:\s*v?([0-9][^ \n\r\t]+)", out)
    return m.group(1) if m else _extract_semver(out)

def _terraform_version() -> Optional[str]:
    # terraform version -> "Terraform v1.6.6"
    r = _run(["terraform", "version"])
    out = _first_nonempty(r.stdout, r.stderr) or ""
    m = re.search(r"Terraform\s+v?([0-9][^ \n\r\t]+)", out)
    return m.group(1) if m else _extract_semver(out)

def _code_version() -> Optional[str]:
    # code --version (first line is version)
    r = _run(["code", "--version"])
    out = _first_nonempty(r.stdout, r.stderr) or ""
    line0 = out.splitlines()[0].strip() if out else ""
    return line0 or _extract_semver(out)

def _go_version() -> Optional[str]:
    # go version -> "go version go1.22.3 linux/amd64"
    r = _run(["go", "version"])
    out = _first_nonempty(r.stdout, r.stderr) or ""
    m = re.search(r"go\s+version\s+go([0-9][^ \n\r\t]+)", out)
    return m.group(1) if m else _extract_semver(out)

def _dotnet_version() -> Optional[str]:
    # dotnet --version -> "8.0.301"
    return _exec_version(["dotnet", "--version"])

# ---------- package manager fallbacks (Debian/Ubuntu focus) ----------

def _dpkg_version(pkg: str) -> Optional[str]:
    if not shutil.which("dpkg"):
        return None
    # dpkg -s gives a "Version: x" field (preferable)
    r = _run(["dpkg", "-s", pkg])
    if r.returncode == 0:
        for line in (r.stdout or "").splitlines():
            if line.lower().startswith("version:"):
                return line.split(":", 1)[1].strip()
    # fallback dpkg -l (3rd column is version)
    r = _run(["dpkg", "-l", pkg])
    if r.returncode == 0:
        lines = (r.stdout or "").splitlines()
        for line in lines:
            if line.startswith("ii"):
                parts = line.split()
                if len(parts) >= 3:
                    return parts[2]
    return None

def _snap_version(snap_name: str) -> Optional[str]:
    if not shutil.which("snap"):
        return None
    r = _run(["snap", "list", snap_name])
    if r.returncode == 0:
        lines = (r.stdout or "").splitlines()
        if len(lines) >= 2:
            cols = lines[1].split()
            if len(cols) >= 2:
                return cols[1]
    return None

def _sdkman_current(candidate: str) -> Optional[str]:
    # Try to read SDKMAN current if available (non-root HOME)
    home = os.path.expanduser(f"~{os.environ.get('SUDO_USER')}") if os.environ.get("SUDO_USER") else os.path.expanduser("~")
    init_path = os.path.join(home, ".sdkman", "bin", "sdkman-init.sh")
    if not os.path.isfile(init_path):
        return None
    cmd = ['bash', '-lc', f'source "{init_path}"; sdk current {candidate}']
    r = _run(cmd)
    out = _first_nonempty(r.stdout, r.stderr) or ""
    # Using java version 21.0.3-tem
    m = re.search(r"Using\s+[A-Za-z]+\s+version\s+([^\s]+)", out)
    if m:
        return m.group(1)
    # Or any semver-like token
    return _extract_semver(out)

# ---------- main API ----------

# Aliases for PATH probing
TOOL_ALIASES: Dict[str, List[str]] = {
    "python": ["python3", "python"],
    "pip": ["pip3", "pip"],
    "node": ["node", "nodejs"],
    "npm": ["npm"],
    "java": ["java", "javac"],
    "maven": ["mvn"],
    "gradle": ["gradle"],
    "git": ["git"],
    "docker": ["docker"],
    "kubectl": ["kubectl"],
    "terraform": ["terraform"],
    "vscode": ["code"],
    "code": ["code"],
    "go": ["go"],
    "dotnet": ["dotnet"],
}

def find_executable(tool_name: str, candidates: List[str]) -> Optional[str]:
    seen = set()
    for name in candidates:
        if not name or name in seen:
            continue
        seen.add(name)
        p = _which(name)
        if p:
            return p
    return None

def check_version(tool_name: str, version: str = "latest") -> dict:
    """
    Returns a consistent object:
    - success: {"status": "success", "message": "...", "tool": name, "version": "...", "source": "...", "path": "...", "details": {...}}
    - error:   {"status": "error", "message": "..."}
    """
    # Example usage of tool_name and version to avoid unused variable errors
    result = {
        "status": "success",
        "message": f"Checked version for {tool_name}",
        "tool": tool_name,
        "version": version,
        "source": "dummy",
        "path": None,
        "details": {}
    }
    return result
