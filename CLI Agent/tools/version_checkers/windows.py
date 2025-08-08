import os
import re
import shutil
import subprocess
from typing import List, Optional, Tuple

try:
    import winreg  # type: ignore
except Exception:  # Keep import safe in case of cross-OS tooling
    winreg = None  # type: ignore


# ---- Internal helpers (self-contained to this file) ----

_VERSION_REGEX = re.compile(r"\b(\d+(?:\.\d+){0,3})\b")


def _parse_version(text: str) -> Optional[str]:
    if not text:
        return None
    m = _VERSION_REGEX.search(text)
    return m.group(1) if m else None


def _try_exec_version(exe: str, extra_args: Optional[List[str]] = None, timeout: int = 6) -> Optional[Tuple[str, str]]:
    """Try common version flags on an executable.

    Returns (version, source) or None.
    """
    if not exe:
        return None
    candidates = [
        [exe, "--version"],
        [exe, "-version"],
        [exe, "-v"],
        [exe, "version"],
    ]
    if extra_args:
        candidates.insert(0, [exe, *extra_args])

    for cmd in candidates:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            # Some tools print version to stderr (e.g., java)
            output = (result.stdout or "").strip() or (result.stderr or "").strip()
            if result.returncode == 0 and output:
                v = _parse_version(output)
                if v:
                    return v, "cli"
        except Exception:
            continue
    return None


def _which_any(names: List[str]) -> Optional[str]:
    for n in names:
        path = shutil.which(n)
        if path:
            return path
    return None


def _read_registry_display_version(tool: str) -> Optional[Tuple[str, str]]:
    """Search Windows Uninstall registry for DisplayVersion by common names.

    Returns (version, source) or None.
    """
    if winreg is None:
        return None

    name_synonyms = {
        "python": ["Python", "Python 3"],
        "node": ["Node.js", "nodejs"],
        "nodejs": ["Node.js", "nodejs"],
        "git": ["Git"],
        "docker": ["Docker Desktop", "Docker"],
        "vscode": ["Visual Studio Code", "Microsoft VS Code"],
        "code": ["Visual Studio Code", "Microsoft VS Code"],
        "java": ["OpenJDK", "Java", "Adoptium", "Temurin"],
        "openjdk": ["OpenJDK", "Temurin", "AdoptOpenJDK"],
        "intellij": ["IntelliJ", "IntelliJ IDEA"],
        "pycharm": ["PyCharm"],
        "eclipse": ["Eclipse"],
    }

    search_terms = name_synonyms.get(tool.lower(), [tool])

    uninstall_roots = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]

    for hive, path in uninstall_roots:
        try:
            key = winreg.OpenKey(hive, path)
        except Exception:
            continue
        try:
            i = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(key, i)
                except OSError:
                    break
                i += 1
                try:
                    sub = winreg.OpenKey(key, subkey_name)
                    display_name, _ = winreg.QueryValueEx(sub, "DisplayName")
                    display_version = None
                    try:
                        display_version, _ = winreg.QueryValueEx(sub, "DisplayVersion")
                    except Exception:
                        pass
                    if isinstance(display_name, str) and any(t.lower() in display_name.lower() for t in search_terms):
                        if display_version and isinstance(display_version, str):
                            v = _parse_version(display_version) or display_version.strip()
                            return str(v), "registry"
                except Exception:
                    continue
        finally:
            try:
                winreg.CloseKey(key)
            except Exception:
                pass
    return None


def _get_file_version_via_powershell(path: str) -> Optional[Tuple[str, str]]:
    if not path or not os.path.exists(path):
        return None
    try:
        ps_cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            f"(Get-Item '{path}').VersionInfo.ProductVersion"
        ]
        result = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=6)
        v = (result.stdout or "").strip()
        if result.returncode == 0 and v:
            v_parsed = _parse_version(v) or v
            return str(v_parsed), "file_version"
    except Exception:
        pass
    return None


def _probe_common_paths(tool: str) -> Optional[Tuple[str, str]]:
    """Try common install locations for popular tools and read EXE file version.

    Returns (version, source) or None.
    """
    pf = os.environ.get("ProgramFiles", r"C:\\Program Files")
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\\Program Files (x86)")
    local = os.environ.get("LOCALAPPDATA", os.path.expanduser(r"~\\AppData\\Local"))

    candidates = []
    t = tool.lower()
    if t in ("vscode", "code"):
        candidates += [
            os.path.join(local, r"Programs\Microsoft VS Code\Code.exe"),
            os.path.join(pf, r"Microsoft VS Code\Code.exe"),
        ]
    elif t in ("docker",):
        candidates += [
            os.path.join(pf, r"Docker\Docker\Docker Desktop.exe"),
        ]
    elif t in ("node", "nodejs"):
        candidates += [
            os.path.join(pf, r"nodejs\node.exe"),
            os.path.join(pf86, r"nodejs\node.exe"),
        ]
    elif t in ("git",):
        candidates += [
            os.path.join(pf, r"Git\cmd\git.exe"),
            os.path.join(pf86, r"Git\cmd\git.exe"),
        ]
    elif t in ("python",):
        # Typical python.org layout
        for d in os.listdir(local) if os.path.isdir(local) else []:
            if d.startswith("Programs\\Python\\Python"):
                candidates.append(os.path.join(local, d, "python.exe"))
        # Fallback known locations
        candidates += [
            os.path.join(pf, r"Python311\python.exe"),
            os.path.join(pf, r"Python312\python.exe"),
        ]
    elif t in ("java", "openjdk", "jdk"):
        # Try common JDK paths
        jdk_base = os.path.join(pf, "Java")
        if os.path.isdir(jdk_base):
            for name in os.listdir(jdk_base):
                if name.lower().startswith("jdk"):
                    candidates.append(os.path.join(jdk_base, name, r"bin\java.exe"))

    for path in candidates:
        if os.path.exists(path):
            # Try CLI flag first if it is a CLI
            cli_try = _try_exec_version(path)
            if cli_try:
                return cli_try
            # Else read file version
            fv = _get_file_version_via_powershell(path)
            if fv:
                return fv
    return None


def check_version(tool, version=None):
    """Enhanced Windows version check that works beyond winget.

    Keeps signature and primary return fields stable. Adds optional version/source.
    """
    # 1) winget listing (existing behavior)
    try:
        result = subprocess.run(["winget", "list", tool], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            lines = (result.stdout or "").splitlines()
            for line in lines:
                if tool.lower() in line.lower():
                    match = _parse_version(line)
                    if match:
                        return {
                            "status": "success",
                            "message": f"{tool} version: {match} (Windows/winget)",
                            "version": match,
                            "source": "winget",
                        }
        # If winget didn't error but also didn't find it, fall through to other methods
    except Exception as e:
        # winget not installed or failed; continue to other methods
        pass

    # 2) PATH/CLI detection
    exe_map = {
        "python": ["py", "python", "python3"],
        "java": ["java"],
        "node": ["node"],
        "nodejs": ["node"],
        "git": ["git"],
        "docker": ["docker"],
        "vscode": ["code"],
        "code": ["code"],
    }
    exe_names = exe_map.get(tool.lower(), [tool])
    exe = _which_any(exe_names)
    if exe:
        # Special: java often needs -version and prints to stderr
        extra = ["-version"] if os.path.basename(exe).lower().startswith("java") else None
        v = _try_exec_version(exe, extra_args=extra)
        if v:
            ver, src = v
            return {
                "status": "success",
                "message": f"{tool} version: {ver} (Windows/{src})",
                "version": ver,
                "source": src,
            }

    # 3) Registry uninstall entries
    reg_v = _read_registry_display_version(tool)
    if reg_v:
        ver, src = reg_v
        return {
            "status": "success",
            "message": f"{tool} version: {ver} (Windows/{src})",
            "version": ver,
            "source": src,
        }

    # 4) Probe common install paths and read EXE version
    file_v = _probe_common_paths(tool)
    if file_v:
        ver, src = file_v
        return {
            "status": "success",
            "message": f"{tool} version: {ver} (Windows/{src})",
            "version": ver,
            "source": src,
        }

    # Fallback: keep previous success-not-found behavior for compatibility
    return {
        "status": "success",
        "message": f"{tool} not found or version not detected (Windows)",
    }
