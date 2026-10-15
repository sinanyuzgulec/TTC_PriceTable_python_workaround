"""
Cross-platform detector for Elder Scrolls Online (ESO) AddOns directory
and TamrielTradeCentre addon installation directory.
Supports: Linux (Steam Proton, Flatpak, Lutris, Bottles, Heroic, Wine, symlinks),
Windows (Standard Documents, OneDrive, Registry/Shell Folders), and macOS.
"""

import os
import re
import sys
import platform
from pathlib import Path
from typing import List, Optional


ESO_APP_ID = "306130"
TTC_FOLDER_NAME = "TamrielTradeCentre"
RELATIVE_ESO_LIVE = os.path.join("Elder Scrolls Online", "live", "AddOns")


def get_platform_name() -> str:
    """Return normalized platform name: 'linux', 'windows', 'darwin'."""
    return platform.system().lower()


def find_steam_library_folders_linux() -> List[Path]:
    """Parse Steam libraryfolders.vdf on Linux to find all Steam library paths."""
    candidates = [
        Path.home() / ".steam" / "steam" / "steamapps" / "libraryfolders.vdf",
        Path.home() / ".steam" / "root" / "steamapps" / "libraryfolders.vdf",
        Path.home() / ".local" / "share" / "Steam" / "steamapps" / "libraryfolders.vdf",
        # Flatpak Steam
        Path.home() / ".var" / "app" / "com.valvesoftware.Steam" / ".steam" / "steam" / "steamapps" / "libraryfolders.vdf",
        Path.home() / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam" / "steamapps" / "libraryfolders.vdf",
    ]

    libraries = set()
    # Always include standard steam locations as fallback
    libraries.add(Path.home() / ".local" / "share" / "Steam")
    libraries.add(Path.home() / ".steam" / "steam")

    for vdf_file in candidates:
        if not vdf_file.is_file():
            continue
        try:
            content = vdf_file.read_text(encoding="utf-8", errors="ignore")
            # Look for "path" "..."
            matches = re.findall(r'"path"\s*"([^"]+)"', content)
            for m in matches:
                p = Path(m).resolve()
                if p.exists():
                    libraries.add(p)
        except Exception:
            pass

    return list(libraries)


def get_windows_documents_path() -> Path:
    """Resolve true Windows Documents folder, including relocated or OneDrive paths."""
    if get_platform_name() == "windows":
        try:
            import ctypes
            from ctypes import wintypes
            # CSIDL_PERSONAL = 5 represents My Documents
            buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            # SHGetFolderPathW(hwnd, csidl, token, flags, path)
            ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf)
            doc_path = Path(buf.value)
            if doc_path.exists():
                return doc_path
        except Exception:
            pass

    # Fallback to standard environment variables
    userprofile = os.environ.get("USERPROFILE")
    if userprofile:
        # Check OneDrive Documents first if present
        onedrive_doc = Path(userprofile) / "OneDrive" / "Documents"
        if onedrive_doc.exists():
            return onedrive_doc
        std_doc = Path(userprofile) / "Documents"
        if std_doc.exists():
            return std_doc

    return Path.home() / "Documents"


def get_candidate_addon_directories() -> List[Path]:
    """
    Return an ordered list of candidate directories where ESO AddOns might be located.
    """
    plat = get_platform_name()
    candidates = []

    if plat == "linux":
        # 1. Steam Proton prefixes (Standard & Flatpak & custom libraries)
        steam_libs = find_steam_library_folders_linux()
        for lib in steam_libs:
            pfx_doc = lib / "steamapps" / "compatdata" / ESO_APP_ID / "pfx" / "drive_c" / "users" / "steamuser" / "Documents"
            candidates.append(pfx_doc / RELATIVE_ESO_LIVE)
            # Some wine setups map directly to user home
            candidates.append(lib / "steamapps" / "compatdata" / ESO_APP_ID / "pfx" / "drive_c" / "users" / os.environ.get("USER", "steamuser") / "Documents" / RELATIVE_ESO_LIVE)

        # 2. Flatpak Steam standard location
        flatpak_pfx = Path.home() / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam" / "steamapps" / "compatdata" / ESO_APP_ID / "pfx" / "drive_c" / "users" / "steamuser" / "Documents" / RELATIVE_ESO_LIVE
        candidates.append(flatpak_pfx)

        # 3. Lutris / Bottles / Heroic / Wine prefixes
        wine_prefixes = [
            Path.home() / "Games" / "elder-scrolls-online" / "drive_c" / "users" / os.environ.get("USER", "steamuser") / "Documents" / RELATIVE_ESO_LIVE,
            Path.home() / "Games" / "Heroic" / "Prefixes" / "default" / "Elder Scrolls Online" / "pfx" / "drive_c" / "users" / "steamuser" / "Documents" / RELATIVE_ESO_LIVE,
            Path.home() / ".wine" / "drive_c" / "users" / os.environ.get("USER", "steamuser") / "Documents" / RELATIVE_ESO_LIVE,
            Path.home() / ".local" / "share" / "bottles" / "bottles" / "ESO" / "drive_c" / "users" / "steamuser" / "Documents" / RELATIVE_ESO_LIVE,
        ]
        candidates.extend(wine_prefixes)

        # 4. Native / Symlink / Minion paths
        candidates.append(Path.home() / "Documents" / RELATIVE_ESO_LIVE)
        candidates.append(Path.home() / RELATIVE_ESO_LIVE)
        candidates.append(Path.home() / "ESO_AddOns")

    elif plat == "windows":
        doc_dir = get_windows_documents_path()
        candidates.append(doc_dir / RELATIVE_ESO_LIVE)

        userprofile = os.environ.get("USERPROFILE", "")
        if userprofile:
            candidates.append(Path(userprofile) / "Documents" / RELATIVE_ESO_LIVE)
            candidates.append(Path(userprofile) / "OneDrive" / "Documents" / RELATIVE_ESO_LIVE)
            candidates.append(Path(userprofile) / "Saved Games" / RELATIVE_ESO_LIVE)

        # Common drive letters if moved manually
        for drive in ("C", "D", "E", "F"):
            candidates.append(Path(f"{drive}:/Documents") / RELATIVE_ESO_LIVE)
            candidates.append(Path(f"{drive}:/Users/{os.environ.get('USERNAME', '')}/Documents") / RELATIVE_ESO_LIVE)

    elif plat == "darwin":  # macOS (Intel & Apple Silicon)
        # Native macOS documents
        candidates.append(Path.home() / "Documents" / RELATIVE_ESO_LIVE)
        # Whisky / CrossOver prefixes on Mac
        candidates.append(Path.home() / "Library" / "Application Support" / "CrossOver" / "Bottles" / "ESO" / "drive_c" / "users" / "crossover" / "Documents" / RELATIVE_ESO_LIVE)
        candidates.append(Path.home() / "Library" / "Application Support" / "com.isaacmarovitz.Whisky" / "Bottles" / "ESO" / "drive_c" / "users" / os.environ.get("USER", "user") / "Documents" / RELATIVE_ESO_LIVE)

    # General fallback
    candidates.append(Path.home() / "Documents" / RELATIVE_ESO_LIVE)

    # Deduplicate while preserving order
    seen = set()
    unique_candidates = []
    for c in candidates:
        norm = str(c.resolve()) if c.exists() else str(c)
        if norm not in seen:
            seen.add(norm)
            unique_candidates.append(c)

    return unique_candidates


def detect_ttc_directory() -> Optional[Path]:
    """
    Detect the TamrielTradeCentre addon directory on the system.
    Returns Path if found, otherwise None.
    Priority:
    1. An existing directory with TamrielTradeCentre folder inside AddOns
    2. An existing AddOns folder (where TamrielTradeCentre can be created)
    """
    candidates = get_candidate_addon_directories()

    # Pass 1: Look for existing TamrielTradeCentre directory
    for addon_dir in candidates:
        ttc_path = addon_dir / TTC_FOLDER_NAME
        if ttc_path.is_dir():
            return ttc_path.resolve()

    # Pass 2: Look for existing AddOns directory (user has ESO AddOns installed, but TTC not yet placed)
    for addon_dir in candidates:
        if addon_dir.is_dir():
            ttc_path = addon_dir / TTC_FOLDER_NAME
            return ttc_path

    return None
