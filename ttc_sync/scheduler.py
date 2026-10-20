"""
Cross-platform scheduler manager for TTC Price Table Sync.
Supports:
- Linux: systemd user timers (primary) and crontab (fallback)
- Windows: Windows Task Scheduler (schtasks via pythonw.exe)
- macOS: launchd LaunchAgents
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Tuple, Optional
from .detector import get_platform_name


SERVICE_NAME = "ttc-sync"
WINDOWS_TASK_NAME = "TTC_PriceTable_Sync"
MACOS_LAUNCH_LABEL = "com.ttc.pricetable.sync"


def get_python_executable(gui: bool = False) -> str:
    """
    Get the Python executable path. On Windows, gui=True prefers pythonw.exe to prevent terminal popups.
    """
    if get_platform_name() == "windows" and gui:
        py_dir = Path(sys.executable).parent
        pythonw = py_dir / "pythonw.exe"
        if pythonw.is_file():
            return str(pythonw)
    return sys.executable


def get_entrypoint_script() -> Path:
    """Return the absolute path to main.py."""
    # Find main.py relative to this module
    this_dir = Path(__file__).resolve().parent
    main_py = (this_dir.parent / "main.py").resolve()
    if main_py.is_file():
        return main_py
    # Fallback to sys.argv[0]
    return Path(sys.argv[0]).resolve()


# =========================================================================
# Linux systemd & cron implementation
# =========================================================================

def is_systemd_available() -> bool:
    """Check if systemctl --user is available and working."""
    if get_platform_name() != "linux":
        return False
    if not shutil.which("systemctl"):
        return False
    try:
        res = subprocess.run(["systemctl", "--user", "is-system-running"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
        return res.returncode in (0, 1)  # 0: running, 1: degraded (still functional)
    except Exception:
        return False


def install_linux_systemd(interval_hours: int = 12) -> Tuple[bool, str]:
    """Install and enable systemd user service and timer."""
    user_systemd_dir = Path.home() / ".config" / "systemd" / "user"
    user_systemd_dir.mkdir(parents=True, exist_ok=True)

    py_exe = get_python_executable()
    script_path = get_entrypoint_script()

    service_file = user_systemd_dir / f"{SERVICE_NAME}.service"
    timer_file = user_systemd_dir / f"{SERVICE_NAME}.timer"

    service_content = f"""[Unit]
Description=Tamriel Trade Centre Price Table Automatic Sync
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart="{py_exe}" "{script_path}" --sync
StandardOutput=journal
StandardError=journal
"""

    if 24 % interval_hours == 0:
        calendar_spec = f"*-*-* 00/{interval_hours}:00:00"
    else:
        calendar_spec = f"*-*-* 00/12:00:00"

    timer_content = f"""[Unit]
Description=Tamriel Trade Centre Price Table Timer (Runs every {interval_hours} hours)

[Timer]
OnBootSec=2min
OnCalendar={calendar_spec}
Persistent=true

[Install]
WantedBy=timers.target
"""

    try:
        service_file.write_text(service_content, encoding="utf-8")
        timer_file.write_text(timer_content, encoding="utf-8")

        subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
        subprocess.run(["systemctl", "--user", "enable", "--now", f"{SERVICE_NAME}.timer"], check=True)
        subprocess.run(["systemctl", "--user", "restart", f"{SERVICE_NAME}.timer"], check=True)
        return True, f"Successfully installed and started systemd user timer '{SERVICE_NAME}.timer' (runs every {interval_hours}h)."
    except Exception as e:
        return False, f"Failed to install systemd timer: {e}"


def uninstall_linux_systemd() -> Tuple[bool, str]:
    """Stop, disable, and remove systemd user timer and service."""
    user_systemd_dir = Path.home() / ".config" / "systemd" / "user"
    service_file = user_systemd_dir / f"{SERVICE_NAME}.service"
    timer_file = user_systemd_dir / f"{SERVICE_NAME}.timer"

    try:
        subprocess.run(["systemctl", "--user", "stop", f"{SERVICE_NAME}.timer"], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        subprocess.run(["systemctl", "--user", "disable", f"{SERVICE_NAME}.timer"], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        if timer_file.exists():
            timer_file.unlink()
        if service_file.exists():
            service_file.unlink()
        subprocess.run(["systemctl", "--user", "daemon-reload"], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        return True, "Successfully removed systemd user timer and service."
    except Exception as e:
        return False, f"Failed to remove systemd timer: {e}"


def install_linux_cron(interval_hours: int = 12) -> Tuple[bool, str]:
    """Install a cron job running every interval_hours."""
    if not shutil.which("crontab"):
        return False, "crontab utility not found."

    py_exe = get_python_executable()
    script_path = get_entrypoint_script()
    cron_comment = "# TTC Price Table Sync"
    cron_line = f"0 */{interval_hours} * * * \"{py_exe}\" \"{script_path}\" --sync >/dev/null 2>&1 {cron_comment}"

    try:
        res = subprocess.run(["crontab", "-l"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        current = res.stdout if res.returncode == 0 else ""

        # Remove previous entry if exists
        lines = [line for line in current.splitlines() if cron_comment not in line]
        lines.append(cron_line)
        new_crontab = "\n".join(lines) + "\n"

        p = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        out, err = p.communicate(input=new_crontab)
        if p.returncode != 0:
            return False, f"Crontab error: {err}"
        return True, f"Successfully installed cron job (runs every {interval_hours}h)."
    except Exception as e:
        return False, f"Failed to install crontab: {e}"


def uninstall_linux_cron() -> Tuple[bool, str]:
    """Remove cron job."""
    if not shutil.which("crontab"):
        return False, "crontab utility not found."

    cron_comment = "# TTC Price Table Sync"
    try:
        res = subprocess.run(["crontab", "-l"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            return True, "No crontab found."

        lines = [line for line in res.stdout.splitlines() if cron_comment not in line]
        new_crontab = "\n".join(lines) + "\n"

        p = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        p.communicate(input=new_crontab)
        return True, "Successfully removed cron job."
    except Exception as e:
        return False, f"Failed to remove cron job: {e}"


# =========================================================================
# Windows Task Scheduler (schtasks)
# =========================================================================

def install_windows_task(interval_hours: int = 12) -> Tuple[bool, str]:
    """Create Windows Scheduled Task using schtasks."""
    py_exe = get_python_executable(gui=True)
    script_path = get_entrypoint_script()

    # Quote command carefully: pythonw.exe "C:\...\main.py" --sync
    task_cmd = f'"{py_exe}" "{script_path}" --sync'

    # Create task running every interval_hours
    cmd = [
        "schtasks", "/Create",
        "/SC", "HOURLY",
        "/MO", str(interval_hours),
        "/TN", WINDOWS_TASK_NAME,
        "/TR", task_cmd,
        "/F",  # Force overwrite if exists
    ]

    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0:
            return True, f"Successfully created Windows Scheduled Task '{WINDOWS_TASK_NAME}' (runs every {interval_hours}h)."
        return False, f"Failed to create Windows Task: {res.stderr or res.stdout}"
    except Exception as e:
        return False, f"Exception executing schtasks: {e}"


def uninstall_windows_task() -> Tuple[bool, str]:
    """Remove Windows Scheduled Task."""
    cmd = ["schtasks", "/Delete", "/TN", WINDOWS_TASK_NAME, "/F"]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0:
            return True, f"Successfully removed Windows Scheduled Task '{WINDOWS_TASK_NAME}'."
        return False, f"Failed to remove Windows Task: {res.stderr or res.stdout}"
    except Exception as e:
        return False, f"Exception executing schtasks: {e}"


# =========================================================================
# macOS launchd LaunchAgent
# =========================================================================

def get_macos_plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{MACOS_LAUNCH_LABEL}.plist"


def install_macos_launchd(interval_hours: int = 12) -> Tuple[bool, str]:
    """Install macOS launchd agent plist running every interval_hours."""
    plist_path = get_macos_plist_path()
    plist_path.parent.mkdir(parents=True, exist_ok=True)

    py_exe = get_python_executable()
    script_path = get_entrypoint_script()
    interval_seconds = interval_hours * 3600
    log_file = Path.home() / ".ttc_sync.log"

    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{MACOS_LAUNCH_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{py_exe}</string>
        <string>{script_path}</string>
        <string>--sync</string>
    </array>
    <key>StartInterval</key>
    <integer>{interval_seconds}</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{log_file}</string>
    <key>StandardErrorPath</key>
    <string>{log_file}</string>
</dict>
</plist>
"""
    try:
        plist_path.write_text(plist_content, encoding="utf-8")
        subprocess.run(["launchctl", "unload", str(plist_path)], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        res = subprocess.run(["launchctl", "load", str(plist_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0:
            return True, f"Successfully installed macOS launchd agent '{MACOS_LAUNCH_LABEL}' (runs every {interval_hours}h)."
        return False, f"launchctl load failed: {res.stderr}"
    except Exception as e:
        return False, f"Exception installing launchd plist: {e}"


def uninstall_macos_launchd() -> Tuple[bool, str]:
    """Unload and remove macOS launchd agent plist."""
    plist_path = get_macos_plist_path()
    try:
        if plist_path.exists():
            subprocess.run(["launchctl", "unload", str(plist_path)], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            plist_path.unlink()
        return True, f"Successfully removed macOS launchd agent '{MACOS_LAUNCH_LABEL}'."
    except Exception as e:
        return False, f"Exception removing launchd agent: {e}"


# =========================================================================
# High-Level Unified Interface
# =========================================================================

def install_scheduler(interval_hours: int = 12) -> Tuple[bool, str]:
    """Install automated task on the current OS."""
    plat = get_platform_name()
    if plat == "linux":
        if is_systemd_available():
            return install_linux_systemd(interval_hours)
        else:
            return install_linux_cron(interval_hours)
    elif plat == "windows":
        return install_windows_task(interval_hours)
    elif plat == "darwin":
        return install_macos_launchd(interval_hours)
    return False, f"Unsupported operating system: {plat}"


def uninstall_scheduler() -> Tuple[bool, str]:
    """Uninstall automated task on the current OS."""
    plat = get_platform_name()
    if plat == "linux":
        # Try both systemd and cron removal to be thorough
        ok_sys, msg_sys = uninstall_linux_systemd()
        ok_cron, msg_cron = uninstall_linux_cron()
        if ok_sys or ok_cron:
            return True, "Scheduler task removed."
        return False, f"Removal failed: {msg_sys}; {msg_cron}"
    elif plat == "windows":
        return uninstall_windows_task()
    elif plat == "darwin":
        return uninstall_macos_launchd()
    return False, f"Unsupported operating system: {plat}"


def get_scheduler_status() -> str:
    """Return human-readable status of the OS scheduler."""
    plat = get_platform_name()
    if plat == "linux":
        if is_systemd_available():
            try:
                res = subprocess.run(
                    ["systemctl", "--user", "is-active", f"{SERVICE_NAME}.timer"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
                if res.stdout.strip() == "active":
                    # Check next trigger time
                    timer_info = subprocess.run(
                        ["systemctl", "--user", "list-timers", f"{SERVICE_NAME}.timer", "--no-pager"],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                    )
                    return f"Active (systemd timer)\n{timer_info.stdout.strip()}"
                return "Inactive (systemd timer installed but not running or disabled)"
            except Exception:
                return "Not installed (systemd)"
        else:
            # Check cron
            try:
                res = subprocess.run(["crontab", "-l"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if "TTC Price Table Sync" in res.stdout:
                    return "Active (Crontab)"
            except Exception:
                pass
            return "Not installed (Crontab)"

    elif plat == "windows":
        try:
            res = subprocess.run(
                ["schtasks", "/Query", "/TN", WINDOWS_TASK_NAME, "/FO", "LIST"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            if res.returncode == 0:
                return f"Active (Windows Task Scheduler: {WINDOWS_TASK_NAME})"
            return "Not installed (Windows Task Scheduler)"
        except Exception:
            return "Unknown / Not installed"

    elif plat == "darwin":
        plist_path = get_macos_plist_path()
        if plist_path.is_file():
            return f"Active (macOS launchd: {MACOS_LAUNCH_LABEL})"
        return "Not installed (macOS launchd)"

    return "Unsupported OS"
