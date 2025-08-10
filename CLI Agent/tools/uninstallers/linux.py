import os
import subprocess
import shutil
import logging
import re
from typing import List, Set

from tools.utils.name_resolver import resolve_tool_name
from tools.utils.os_utils import (
    get_linux_distro,
    get_available_package_manager,
    is_sudo_available,
    is_snap_available,
)

logger = logging.getLogger(__name__)

# ---------- helpers ----------

def _run(cmd: List[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True)
    except Exception as e:
        return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr=str(e))

def _sudoify(cmd: List[str]) -> List[str]:
    if is_sudo_available():
        return ["sudo"] + cmd
    return cmd

def _dpkg_installed_packages_matching(patterns: List[re.Pattern]) -> Set[str]:
    pkgs: Set[str] = set()
    if not shutil.which("dpkg"):
        return pkgs
    r = _run(["dpkg", "-l"])
    if r.returncode != 0:
        return pkgs
    for line in (r.stdout or "").splitlines():
        if not line.startswith("ii"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        name = parts[1]
        if any(p.search(name) for p in patterns):
            pkgs.add(name)
    return pkgs

def _dpkg_owner_of(path: str) -> str | None:
    if not shutil.which("dpkg-query"):
        return None
    r = _run(["dpkg-query", "-S", path])
    # Output like: openjdk-17-jre-headless: /usr/lib/jvm/java-17-openjdk-amd64/bin/java
    if r.returncode == 0:
        line = (r.stdout or "").strip().splitlines()[0] if r.stdout else ""
        if ":" in line:
            return line.split(":", 1)[0].strip()
    return None

def _snap_is_installed(pkg: str) -> bool:
    if not is_snap_available():
        return False
    r = _run(["snap", "list", pkg])
    return r.returncode == 0

def is_package_installed(pkg_name: str, pkg_manager: str) -> bool:
    try:
        if pkg_manager == "apt":
            result = subprocess.run(
                ["dpkg-query", "-W", "-f=${Status}", pkg_name],
                capture_output=True, text=True
            )
            return "install ok installed" in result.stdout
        elif pkg_manager == "dnf":
            result = subprocess.run(
                ["dnf", "list", "installed", pkg_name],
                capture_output=True, text=True
            )
            return pkg_name in result.stdout
        elif pkg_manager == "snap":
            return _snap_is_installed(pkg_name)
        return False
    except Exception as e:
        logger.warning(f"Failed to check if {pkg_name} is installed: {e}")
        return False

def _apt_purge(packages: List[str]) -> tuple[list[str], list[str]]:
    """Batch purge with autoremove; returns (success, failed) lists."""
    success, failed = [], []
    if not packages:
        return success, failed
    cmd = _sudoify(["apt-get", "purge", "-y"] + packages)
    r = _run(cmd)
    if r.returncode != 0:
        # Try one-by-one to salvage partial success
        for pkg in packages:
            rr = _run(_sudoify(["apt-get", "purge", "-y", pkg]))
            if rr.returncode == 0 or "is not installed" in (rr.stderr or rr.stdout).lower():
                success.append(pkg)
            else:
                failed.append(pkg)
    else:
        success.extend(packages)

    # Autoremove to clear residuals
    _run(_sudoify(["apt-get", "autoremove", "-y", "--purge"]))
    # Optional cleanup
    _run(_sudoify(["apt-get", "clean"]))
    return success, failed

def _dnf_remove(packages: List[str]) -> tuple[list[str], list[str]]:
    success, failed = [], []
    if not packages:
        return success, failed
    cmd = _sudoify(["dnf", "remove", "-y"] + packages)
    r = _run(cmd)
    if r.returncode == 0:
        success.extend(packages)
    else:
        # Try one-by-one
        for pkg in packages:
            rr = _run(_sudoify(["dnf", "remove", "-y", pkg]))
            (success if rr.returncode == 0 else failed).append(pkg)
    return success, failed

def run_uninstall_cmd(tool_name: str, manager: str) -> bool:
    try:
        if manager == "apt":
            cmd = ["apt-get", "purge", "-y", tool_name]
        elif manager == "dnf":
            cmd = ["dnf", "remove", "-y", tool_name]
        elif manager == "snap" and is_snap_available():
            cmd = ["snap", "remove", tool_name]
        else:
            logger.warning(f"Unsupported or unavailable package manager: {manager}")
            return False

        cmd = _sudoify(cmd)
        result = _run(cmd)
        if result.returncode == 0:
            # For apt, follow with autoremove to clean residuals
            if manager == "apt":
                _run(_sudoify(["apt-get", "autoremove", "-y", "--purge"]))
            logger.info(f"{tool_name} uninstalled successfully.")
            return True
        else:
            logger.error(f"Failed to uninstall {tool_name}: {result.stderr.strip() or result.stdout.strip()}")
            return False
    except Exception as e:
        logger.exception(f"Exception during uninstall: {e}")
        return False

def get_java_alternatives(name: str = "java") -> list[str]:
    """
    Detect installed Java alternatives for a given name (e.g., java, javac).
    Returns a list of binary paths.
    """
    try:
        result = subprocess.run(
            ["update-alternatives", "--list", name],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except Exception:
        pass
    return []

def get_related_packages_from_alternatives() -> Set[str]:
    """
    Use update-alternatives targets to discover owning packages.
    """
    java_names = [
        "java", "javac", "keytool", "jar", "javadoc", "jarsigner", "jshell",
        "jcmd", "jconsole", "jdb", "jfr", "jlink", "jmap", "jps", "jstack",
        "rmiregistry", "rmid"
    ]
    packages: Set[str] = set()
    for name in java_names:
        for path in get_java_alternatives(name):
            owner = _dpkg_owner_of(path)
            if owner:
                packages.add(owner)
    return packages

def cleanup_java_alternatives():
    names = [
        "java", "javac", "keytool", "jar", "javadoc", "jarsigner", "jshell",
        "jcmd", "jconsole", "jdb", "jfr", "jlink", "jmap", "jps", "jstack",
        "rmiregistry", "rmid"
    ]
    for n in names:
        # update-alternatives --remove-all <name> (ignore failures)
        _run(_sudoify(["update-alternatives", "--remove-all", n]))

def get_related_packages(alternatives: list[str]) -> list[str]:
    """
    Given a list of java binary paths from alternatives,
    extract related package names like openjdk-17-jdk (fallback heuristic).
    """
    packages = set()
    for alt in alternatives:
        owner = _dpkg_owner_of(alt)
        if owner:
            packages.add(owner)
            continue
        parts = alt.split("/")
        for p in parts:
            if "openjdk" in p or "jdk" in p or "java" in p:
                packages.add(p)
    return list(packages)

# ---------- main API ----------

def uninstall_linux_tool(tool: str, version: str | None = None):
    success, failed = [], []

    distro = get_linux_distro()
    pkg_manager = get_available_package_manager()

    if not pkg_manager:
        return {"status": "error", "message": "No supported package manager found."}

    resolved = resolve_tool_name(tool, "linux", context="uninstall", version=version)
    pkg_name = resolved.get("apt_name") or resolved.get("name") or tool
    snap_name = resolved.get("snap_name") or pkg_name
    logger.info(f"Resolved uninstall package: apt='{pkg_name}', snap='{snap_name}'")

    # Special handling for Java families
    if pkg_name in ["openjdk", "default-jdk", "default-jre", "jdk", "jre", "java",
                    "openjdk-8-jdk", "openjdk-11-jdk", "openjdk-17-jdk", "openjdk-21-jdk",
                    "openjdk-8-jre", "openjdk-11-jre", "openjdk-17-jre", "openjdk-21-jre",
                    "openjdk-8-jre-headless", "openjdk-11-jre-headless", "openjdk-17-jre-headless", "openjdk-21-jre-headless"]:
        # Build package set from:
        # 1) dpkg -l matching openjdk/default jdk/jre families (optionally filter by version)
        patterns = [
            re.compile(r"^openjdk-\d+-jdk$"),
            re.compile(r"^openjdk-\d+-jre$"),
            re.compile(r"^openjdk-\d+-jre-headless$"),
            re.compile(r"^default-jdk$"),
            re.compile(r"^default-jre$"),
        ]
        pkgs = _dpkg_installed_packages_matching(patterns)

        # 2) update-alternatives owners for java toolchain
        pkgs |= get_related_packages_from_alternatives()

        # 3) If explicit version requested (e.g., 17), filter
        if version:
            v = re.sub(r"\D", "", str(version))  # digits only
            if v:
                pkgs = {p for p in pkgs if f"-{v}-" in p or p.endswith(f"-{v}")}

        # Always include the resolved name if installed
        if is_package_installed(pkg_name, pkg_manager="apt"):
            pkgs.add(pkg_name)

        # Purge via apt/dnf
        if pkg_manager == "apt":
            s, f = _apt_purge(sorted(pkgs))
            success.extend(s)
            failed.extend(f)
        elif pkg_manager == "dnf":
            s, f = _dnf_remove(sorted(pkgs))
            success.extend(s)
            failed.extend(f)
        else:
            # Try basic manager removal
            if is_package_installed(pkg_name, pkg_manager):
                if run_uninstall_cmd(pkg_name, pkg_manager):
                    success.append(pkg_name)
                else:
                    failed.append(pkg_name)

        # Clean up alternatives so no stale symlinks remain
        cleanup_java_alternatives()

        # Optional: remove SDKMAN-installed Java candidates
        try:
            sudo_user = os.environ.get("SUDO_USER")
            home = os.path.expanduser(f"~{sudo_user}") if sudo_user else os.path.expanduser("~")
            sdk_init = os.path.join(home, ".sdkman", "bin", "sdkman-init.sh")
            if os.path.isfile(sdk_init):
                # Uninstall all installed SDKMAN Java versions
                cmd = ['bash', '-lc', f'source "{sdk_init}"; ls "$SDKMAN_DIR/candidates/java" 2>/dev/null || true']
                r = _run(cmd)
                for ver in (r.stdout or "").splitlines():
                    ver = ver.strip()
                    if not ver:
                        continue
                    _run(['bash', '-lc', f'source "{sdk_init}"; sdk uninstall java {ver}'])
        except Exception:
            pass

    else:
        # Non-Java: try apt/dnf first, then snap
        if pkg_manager in ("apt", "dnf"):
            if is_package_installed(pkg_name, pkg_manager):
                if run_uninstall_cmd(pkg_name, pkg_manager):
                    success.append(pkg_name)
                else:
                    failed.append(pkg_name)
            else:
                logger.info(f"{pkg_name} is not installed via {pkg_manager}.")
        # Snap fallback
        if is_snap_available() and _snap_is_installed(snap_name):
            if run_uninstall_cmd(snap_name, "snap"):
                success.append(snap_name)
            else:
                failed.append(snap_name)

    if failed:
        return {
            "status": "partial" if success else "error",
            "message": f"Uninstall finished. Success: {success}. Failed: {failed}"
        }
    else:
        return {
            "status": "success",
            "message": f"Uninstalled: {success}" if success else "Nothing to uninstall. Packages not found."
        }