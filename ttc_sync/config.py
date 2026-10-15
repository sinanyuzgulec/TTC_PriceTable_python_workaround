"""
Configuration management for TTC Price Table Sync.
Handles JSON persistence, smart defaults, and CLI overrides.
"""

import os
import json
import platform
from pathlib import Path
from typing import Optional, Dict, Any
from .detector import detect_ttc_directory, get_platform_name


DEFAULT_INTERVAL_HOURS = 12
DEFAULT_SERVER = "eu"


def get_default_config_path() -> Path:
    """Return platform-appropriate path for persistent config."""
    # Check if a local config exists in current working dir or next to project
    local_cfg = Path("ttc_config.json")
    if local_cfg.is_file():
        return local_cfg.resolve()

    plat = get_platform_name()
    if plat == "windows":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
        cfg_dir = base / "ttc_sync"
    else:  # Linux, macOS, etc.
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        base = Path(xdg_config) if xdg_config else Path.home() / ".config"
        cfg_dir = base / "ttc_sync"

    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / "config.json"


class Config:
    def __init__(self, config_file: Optional[Path] = None):
        self.config_path = config_file or get_default_config_path()
        self.data: Dict[str, Any] = {
            "target_dir": None,
            "server": DEFAULT_SERVER,
            "interval_hours": DEFAULT_INTERVAL_HOURS,
            "last_sync_timestamp": None,
            "last_sync_files": [],
            "last_sync_bytes": 0,
            "last_sync_status": None,
        }
        self.load()

    def load(self) -> None:
        """Load settings from config file if it exists."""
        if self.config_path.is_file():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    if isinstance(saved, dict):
                        self.data.update(saved)
            except Exception:
                pass

    def save(self) -> None:
        """Save current configuration to JSON file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[Warning] Failed to save config: {e}")

    @property
    def target_dir(self) -> Optional[Path]:
        val = self.data.get("target_dir")
        if val:
            return Path(val)
        # Attempt auto-detection
        detected = detect_ttc_directory()
        if detected:
            self.data["target_dir"] = str(detected)
            self.save()
            return detected
        return None

    @target_dir.setter
    def target_dir(self, path: Path) -> None:
        self.data["target_dir"] = str(Path(path).resolve())
        self.save()

    @property
    def server(self) -> str:
        s = str(self.data.get("server", DEFAULT_SERVER)).lower()
        if s not in ("eu", "na", "both"):
            return DEFAULT_SERVER
        return s

    @server.setter
    def server(self, val: str) -> None:
        val = val.lower().strip()
        if val in ("eu", "na", "both"):
            self.data["server"] = val
            self.save()
        else:
            raise ValueError(f"Invalid server '{val}'. Must be 'eu', 'na', or 'both'.")

    @property
    def interval_hours(self) -> int:
        try:
            return int(self.data.get("interval_hours", DEFAULT_INTERVAL_HOURS))
        except (ValueError, TypeError):
            return DEFAULT_INTERVAL_HOURS

    @interval_hours.setter
    def interval_hours(self, val: int) -> None:
        if val < 1:
            val = 1
        self.data["interval_hours"] = val
        self.save()

    def record_sync_success(self, files: list, total_bytes: int) -> None:
        """Record successful sync metadata."""
        import datetime
        self.data["last_sync_timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.data["last_sync_files"] = files
        self.data["last_sync_bytes"] = total_bytes
        self.data["last_sync_status"] = "success"
        self.save()

    def record_sync_failure(self, error_msg: str) -> None:
        """Record sync failure."""
        import datetime
        self.data["last_sync_timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.data["last_sync_status"] = f"failed: {error_msg}"
        self.save()
