# Linux version checker: probes PATH tools, then dpkg/snap/SDKMAN fallbacks.
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
    """Run a command with timeout; always return a CompletedProcess."""
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception as e:
        return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr=str(e))

def _which(name: str) -> Optional[str]:
    """Locate an executable on PATH."""
    return shutil.which(name)

def _first_nonempty(*vals: Optional[str]) -> Optional[str]:
    """Return the first non-empty string or None."""
    for v in vals:
        if v:
            v = v.strip()
            if v:
                return v
    return None

def _strip_v(s: str) -> str:
    """Strip a leading 'v' (e.g., v18.19.0 -> 18.19.0)."""
    return s[1:] if s and s.startswith("v") else s

def _extract_semver(text: str) -> Optional[str]:
    """Extract a semver-like version from free-form text."""
    # Prefer semver-ish first
    m = re.search(r"\b(\d+\.\d+\.\d+(?:[-+._][0-9A-Za-z.-]+)?)\b", text)
    if m:
        return m.group(1)
    # Fallback to simpler numeric versions
    m = re.search(r"\b(\d{1,4}(?:\.\d+){0,2})\b", text)
    if m:
        return m.group(1)
    return None

def _exec_version(cmd: List[str], strip_leading_v: bool = False) -> Optional[str]:
    """Execute a version command and parse a version from its output."""
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
    """Parse 'java -version' output."""
    r = _run(["java", "-version"])
    out = _first_nonempty(r.stdout, r.stderr) or ""
    # Patterns:
    # openjdk version "17.0.9" 2023-10-17
    # java version "1.8.0_362"
    m = re.search(r'version\s+"([^"]+)"', out)
    if m:
        return m.group(1)
    return _extract_semver(out)

def _maven_version() -> Optional[str]:
    """Parse Maven version from 'mvn -v'."""
    r = _run(["mvn", "-v"])
    out = _first_nonempty(r.stdout, r.stderr) or ""
    m = re.search(r"Apache Maven\s+([0-9][^ \n\r\t]+)", out)
    return m.group(1) if m else _extract_semver(out)

def _gradle_version() -> Optional[str]:
    """Parse Gradle version from 'gradle -v'."""
    r = _run(["gradle", "-v"])
    out = _first_nonempty(r.stdout, r.stderr) or ""
    m = re.search(r"Gradle\s+([0-9][^ \n\r\t]+)", out)
    return m.group(1) if m else _extract_semver(out)

def _kubectl_version() -> Optional[str]:
    """Parse kubectl client version."""
    r = _run(["kubectl", "version", "--client", "--short"])
    out = _first_nonempty(r.stdout, r.stderr) or ""
    m = re.search(r"Client Version:\s*v?([0-9][^ \n\r\t]+)", out)
    return m.group(1) if m else _extract_semver(out)

def _terraform_version() -> Optional[str]:
    """Parse Terraform version."""
    r = _run(["terraform", "version"])
    out = _first_nonempty(r.stdout, r.stderr) or ""
    m = re.search(r"Terraform\s+v?([0-9][^ \n\r\t]+)", out)
    return m.group(1) if m else _extract_semver(out)

def _code_version() -> Optional[str]:
    """Parse VS Code version (first line of 'code --version')."""
    r = _run(["code", "--version"])
    out = _first_nonempty(r.stdout, r.stderr) or ""
    line0 = out.splitlines()[0].strip() if out else ""
    return line0 or _extract_semver(out)

def _go_version() -> Optional[str]:
    """Parse Go version from 'go version'."""
    r = _run(["go", "version"])
    out = _first_nonempty(r.stdout, r.stderr) or ""
    m = re.search(r"go\s+version\s+go([0-9][^ \n\r\t]+)", out)
    return m.group(1) if m else _extract_semver(out)

def _dotnet_version() -> Optional[str]:
    """Parse .NET SDK version."""
    return _exec_version(["dotnet", "--version"])

def _java_default_alternative_path() -> Optional[str]:
    """Resolve the real java path (update-alternatives or which)."""
    # Resolve the real target behind /etc/alternatives/java if present
    alt = "/etc/alternatives/java"
    if os.path.exists(alt):
        r = _run(["readlink", "-f", alt])
        if r.returncode == 0:
            return (r.stdout or "").strip()
    # Fallback to which java
    p = shutil.which("java")
    if p:
        r = _run(["readlink", "-f", p])
        if r.returncode == 0 and (r.stdout or "").strip():
            return (r.stdout or "").strip()
        return p
    return None

def _infer_java_version_from_path(p: str) -> Optional[str]:
    """Infer Java version from common directory names in path."""
    # e.g., /usr/lib/jvm/java-17-openjdk-amd64/bin/java -> 17
    m = re.search(r"/java-(\d{1,3})[-/]", p)
    if m:
        return m.group(1)
    # e.g., .../jdk-17.0.9/...
    m = re.search(r"/jdk-?([0-9][0-9._-]*)/", p)
    if m:
        return m.group(1)
    return None

def _java_alternatives_info() -> dict:
    """List java alternatives and inferred versions."""
    info = {"current_path": _java_default_alternative_path(), "alternatives": []}
    r = _run(["update-alternatives", "--list", "java"])
    if r.returncode == 0:
        lines = [(r.stdout or "").strip().splitlines()]
        for path in (lines[0] if lines and lines[0] else []):
            path = path.strip()
            if not path:
                continue
            info["alternatives"].append({
                "path": path,
                "inferred_version": _infer_java_version_from_path(path)
            })
    return info

def _dpkg_java_packages() -> list[dict]:
    """List installed Java-related packages via dpkg."""
    if not shutil.which("dpkg"):
        return []
    r = _run(["dpkg", "-l"])
    pkgs = []
    if r.returncode == 0:
        for line in (r.stdout or "").splitlines():
            if not line.startswith("ii"):
                continue
            parts = line.split()
            if len(parts) < 3:
                continue
            name, ver = parts[1], parts[2]
            if name.startswith("openjdk-") or name in ("default-jdk", "default-jre"):
                pkgs.append({"name": name, "version": ver})
    return pkgs

def _sdkman_java_installed() -> dict:
    """List SDKMAN Java installations and the current one."""
    out = {"installed": [], "current": None}
    home = os.path.expanduser(f"~{os.environ.get('SUDO_USER')}") if os.environ.get("SUDO_USER") else os.path.expanduser("~")
    init_path = os.path.join(home, ".sdkman", "bin", "sdkman-init.sh")
    if not os.path.isfile(init_path):
        return out
    # List installed SDKMAN java candidates (directories under candidates/java)
    r = _run(['bash', '-lc', f'source "{init_path}"; ls "$SDKMAN_DIR/candidates/java" 2>/dev/null || true'])
    if r.returncode == 0:
        for line in (r.stdout or "").splitlines():
            v = line.strip()
            if v and v != "current":
                out["installed"].append(v)
    out["current"] = _sdkman_current("java")
    return out

# ---------- package manager fallbacks (Debian/Ubuntu focus) ----------

def _dpkg_version(pkg: str) -> Optional[str]:
    """Get package version from dpkg (installed package metadata)."""
    if not shutil.which("dpkg"):
        return None
    r = _run(["dpkg", "-s", pkg])
    if r.returncode == 0:
        for line in (r.stdout or "").splitlines():
            if line.lower().startswith("version:"):
                return line.split(":", 1)[1].strip()
    r = _run(["dpkg", "-l", pkg])
    if r.returncode == 0:
        for line in (r.stdout or "").splitlines():
            if line.startswith("ii"):
                parts = line.split()
                if len(parts) >= 3:
                    return parts[2]
    return None

def _snap_version(snap_name: str) -> Optional[str]:
    """Get version from snap list for a specific snap."""
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
    """Get current SDKMAN version for a candidate (e.g., java, maven)."""
    # Read SDKMAN current for non-root user if present
    home = os.path.expanduser(f"~{os.environ.get('SUDO_USER')}") if os.environ.get("SUDO_USER") else os.path.expanduser("~")
    init_path = os.path.join(home, ".sdkman", "bin", "sdkman-init.sh")
    if not os.path.isfile(init_path):
        return None
    cmd = ['bash', '-lc', f'source "{init_path}"; sdk current {candidate}']
    r = _run(cmd)
    out = _first_nonempty(r.stdout, r.stderr) or ""
    m = re.search(r"Using\s+[A-Za-z]+\s+version\s+([^\s]+)", out)
    if m:
        return m.group(1)
    return _extract_semver(out)

# ---------- main API ----------

# Mapping of common aliases to probe for each tool.
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
    """Return the first candidate found on PATH."""
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
    Version detection order (Linux):
      1) Execute tool (preferred)
      2) dpkg (Debian/Ubuntu)
      3) snap
      4) SDKMAN current (if candidate is known)
    Returns:
      - success: {"status":"success","tool":..., "version":..., "source":..., "path":...}
      - error:   {"status":"error","message":...}
    """
    normalized = (tool_name or "").strip().lower()
    resolved = resolve_tool_name(normalized, os_type="linux", version=version, context="version_check") or {}

    apt_name = resolved.get("apt_name") or resolved.get("name") or normalized
    snap_name = resolved.get("snap_name") or normalized
    sdk_candidate = resolved.get("sdk_candidate")

    # PATH probing names
    alias_list = TOOL_ALIASES.get(normalized, [normalized])
    probe_names = list(dict.fromkeys(alias_list + [apt_name, snap_name, resolved.get("name", normalized)]))

    # Shortcut: Java via 'java --version' only (avoid JDK/JRE package noise)
    java_like = normalized == "java" or ("java" in normalized) or ("jdk" in normalized) or normalized in ("default-jdk", "default-jre")
    if java_like:
        r = _run(["java", "--version"])
        if r.returncode == 0:
            out = ((r.stdout or "") + "\n" + (r.stderr or "")).strip()
            first_line = out.splitlines()[0].strip() if out else ""
            m = re.search(r"\b(\d{1,4}(?:\.\d+){0,3}(?:_[0-9]+)?)\b", first_line)
            ver = m.group(1) if m else first_line or "unknown"
            return {
                "status": "success",
                "message": f"java version {ver} via executable",
                "tool": "java",
                "version": ver,
                "source": "executable",
                "path": shutil.which("java") or "",
            }
        return {
            "status": "error",
            "message": "java --version failed or Java is not installed."
        }

    # 1) Direct executable probe
    exe_path = find_executable(normalized, probe_names)
    detected_version = None
    tool_key = normalized

    if exe_path:
        if normalized in ("maven", "mvn"):
            detected_version = _maven_version()
            tool_key = "maven"
        elif normalized == "gradle":
            detected_version = _gradle_version()
        elif normalized == "kubectl":
            detected_version = _kubectl_version()
        elif normalized == "terraform":
            detected_version = _terraform_version()
        elif normalized in ("vscode", "code"):
            detected_version = _code_version()
            tool_key = "vscode"
        elif normalized == "go":
            detected_version = _go_version()
        elif normalized == "dotnet":
            detected_version = _dotnet_version()
        elif normalized in ("node", "nodejs"):
            detected_version = _exec_version([exe_path, "--version"], strip_leading_v=True)
            tool_key = "node"
        elif normalized == "npm":
            detected_version = _exec_version([exe_path, "--version"], strip_leading_v=True)
        else:
            detected_version = (
                _exec_version([exe_path, "--version"]) or
                _exec_version([exe_path, "-v"]) or
                _exec_version([exe_path, "-V"]) or
                _exec_version([exe_path, "version"])
            )

        if detected_version:
            return {
                "status": "success",
                "message": f"{tool_key} version {detected_version} via executable",
                "tool": tool_key,
                "version": detected_version,
                "source": "executable",
                "path": exe_path,
            }

    # 2) dpkg metadata (non-Java)
    ver = _dpkg_version(apt_name)
    if ver:
        return {
            "status": "success",
            "message": f"{normalized} version {ver} via dpkg (package {apt_name})",
            "tool": normalized,
            "version": ver,
            "source": "dpkg",
            "path": exe_path or _which(tool_name) or _which(apt_name) or "",
        }

    # 3) snap metadata (non-Java)
    ver = _snap_version(snap_name)
    if ver:
        return {
            "status": "success",
            "message": f"{normalized} version {ver} via snap (package {snap_name})",
            "tool": normalized,
            "version": ver,
            "source": "snap",
            "path": exe_path or _which(tool_name) or _which(snap_name) or "",
        }

    # 4) SDKMAN current (non-Java candidates)
    if sdk_candidate:
        ver = _sdkman_current(sdk_candidate)
        if ver:
            return {
                "status": "success",
                "message": f"{normalized} version {ver} via SDKMAN",
                "tool": normalized,
                "version": ver,
                "source": "sdkman",
                "path": exe_path or "",
            }

    # Nothing found
    return {
        "status": "error",
        "message": f"{tool_name} is not installed, not in PATH, or version could not be determined."
    }
