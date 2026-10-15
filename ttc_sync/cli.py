"""
Command Line Interface (CLI) for Tamriel Trade Centre (TTC) Price Table Sync.
Provides rich output, interactive status, manual sync, daemon mode,
and automated OS scheduler installation.
"""

import os
import sys
import time
import signal
import logging
import argparse
from pathlib import Path
from datetime import datetime, timezone

from .config import Config, DEFAULT_INTERVAL_HOURS, DEFAULT_SERVER
from .detector import detect_ttc_directory, get_platform_name
from .downloader import sync_price_table, DownloadError
from .scheduler import install_scheduler, uninstall_scheduler, get_scheduler_status


# Terminal styling
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def supports_color() -> bool:
    """Check if terminal supports ANSI styling."""
    if os.environ.get("NO_COLOR"):
        return False
    if not sys.stdout.isatty():
        return False
    return True


def cprint(text: str, color: str = "", bold: bool = False):
    """Print with optional ANSI colors."""
    if supports_color():
        prefix = f"{Colors.BOLD if bold else ''}{color}"
        print(f"{prefix}{text}{Colors.RESET}")
    else:
        print(text)


def setup_logger(log_file: Path) -> logging.Logger:
    """Configure logger that writes to both console and log file."""
    logger = logging.getLogger("ttc_sync")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    # File handler
    try:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.INFO)
        fh_formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        fh.setFormatter(fh_formatter)
        logger.addHandler(fh)
    except Exception:
        pass

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch_formatter = logging.Formatter("%(message)s")
    ch.setFormatter(ch_formatter)
    logger.addHandler(ch)

    return logger


def print_disclaimer():
    """Display mandatory legal & service disclaimer before execution."""
    cprint("┌──────────────────────────────────────────────────────────────┐", Colors.YELLOW)
    cprint("│                      LEGAL DISCLAIMER                        │", Colors.YELLOW, bold=True)
    cprint("├──────────────────────────────────────────────────────────────┤", Colors.YELLOW)
    cprint("│ • Unofficial community tool for The Elder Scrolls Online.    │", Colors.YELLOW)
    cprint("│ • Not affiliated with ZeniMax Online Studios or TTC Gaming.  │", Colors.YELLOW)
    cprint("│ • Not responsible for any issues arising on or related to    │", Colors.YELLOW)
    cprint("│   https://eu.tamrieltradecentre.com/pc/Trade/WebClient       │", Colors.YELLOW)
    cprint("│ • Strictly downloads zip data & extracts ONLY .lua tables.   │", Colors.YELLOW)
    cprint("└──────────────────────────────────────────────────────────────┘", Colors.YELLOW)


def print_banner():
    cprint("╔══════════════════════════════════════════════════════════════╗", Colors.CYAN)
    cprint("║       Tamriel Trade Centre - Price Table Auto-Sync           ║", Colors.CYAN, bold=True)
    cprint("║      Cross-Platform Automated Price Table Updater for ESO    ║", Colors.CYAN)
    cprint("╚══════════════════════════════════════════════════════════════╝", Colors.CYAN)
    print_disclaimer()


def show_status(config: Config):
    """Print detailed system and configuration status."""
    print_banner()

    target_dir = config.target_dir
    plat = get_platform_name()

    cprint("\n[ System & Path Status ]", Colors.BOLD)
    print(f"  • Operating System   : {plat.capitalize()} ({sys.platform})")
    print(f"  • Config Location    : {config.config_path}")
    print(f"  • Configured Server  : {config.server.upper()}")
    print(f"  • Sync Interval      : Every {config.interval_hours} hours")

    if target_dir:
        cprint(f"  • TTC AddOn Path     : {target_dir}", Colors.GREEN if target_dir.exists() else Colors.YELLOW)
        exists_str = "Found" if target_dir.exists() else "Directory does not exist yet (will be created)"
        print(f"  • AddOn Status       : {exists_str}")

        # Check existing PriceTable files
        if target_dir.exists():
            price_eu = target_dir / "PriceTableEU.lua"
            price_na = target_dir / "PriceTableNA.lua"

            cprint("\n[ Installed Price Table Files ]", Colors.BOLD)
            found_any = False
            for p, name in [(price_eu, "PriceTableEU.lua"), (price_na, "PriceTableNA.lua")]:
                if p.exists():
                    found_any = True
                    mtime = datetime.fromtimestamp(p.stat().st_mtime, timezone.utc)
                    age_h = (datetime.now(timezone.utc) - mtime).total_seconds() / 3600
                    size_mb = p.stat().st_size / (1024 * 1024)
                    cprint(f"  • {name:<18} : {size_mb:.2f} MB (Updated: {mtime.strftime('%Y-%m-%d %H:%M UTC')}, ~{age_h:.1f}h ago)", Colors.CYAN)

            if not found_any:
                cprint("  • No PriceTableEU.lua or PriceTableNA.lua found yet in addon directory.", Colors.YELLOW)
    else:
        cprint("  • TTC AddOn Path     : Not detected! Please specify with --path", Colors.RED, bold=True)

    cprint("\n[ Last Sync Info ]", Colors.BOLD)
    print(f"  • Status             : {config.data.get('last_sync_status') or 'Never run'}")
    print(f"  • Timestamp          : {config.data.get('last_sync_timestamp') or 'N/A'}")
    print(f"  • Files Updated      : {len(config.data.get('last_sync_files', []))} files")
    print(f"  • Total Bytes        : {config.data.get('last_sync_bytes', 0):,} bytes")

    cprint("\n[ Background Scheduler Status ]", Colors.BOLD)
    sched_status = get_scheduler_status()
    cprint(f"  {sched_status}", Colors.GREEN if "Active" in sched_status else Colors.YELLOW)
    print()


def execute_sync(config: Config, logger: logging.Logger) -> bool:
    """Execute download and extraction."""
    target_dir = config.target_dir
    if not target_dir:
        logger.error(f"{Colors.RED}[Error] Could not find ESO TamrielTradeCentre addon directory.{Colors.RESET}")
        logger.error("Please specify your addon path manually using: python3 main.py --path \"/path/to/TamrielTradeCentre\"")
        return False

    logger.info(f"{Colors.CYAN}Starting TTC PriceTable synchronization...{Colors.RESET}")
    logger.info(f"Target Directory: {target_dir}")
    logger.info(f"Target Server   : {config.server.upper()}")

    try:
        files, total_bytes = sync_price_table(target_dir, server=config.server, log_fn=logger.info)
        config.record_sync_success(files, total_bytes)
        logger.info(f"{Colors.GREEN}[✓] Successfully synced {len(files)} files ({total_bytes:,} bytes)!{Colors.RESET}")
        return True
    except DownloadError as e:
        config.record_sync_failure(str(e))
        logger.error(f"{Colors.RED}[!] Sync Failed: {e}{Colors.RESET}")
        return False
    except Exception as e:
        config.record_sync_failure(str(e))
        logger.error(f"{Colors.RED}[!] Unexpected error: {e}{Colors.RESET}")
        return False


def run_daemon(config: Config, logger: logging.Logger):
    """Run persistent loop syncing every interval_hours."""
    logger.info(f"{Colors.GREEN}Daemon mode started. Syncing every {config.interval_hours} hours. (Press Ctrl+C to stop){Colors.RESET}")

    running = True

    def signal_handler(sig, frame):
        nonlocal running
        logger.info(f"\n{Colors.YELLOW}Stopping daemon gracefully...{Colors.RESET}")
        running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    while running:
        execute_sync(config, logger)
        logger.info(f"Next sync in {config.interval_hours} hours...")

        # Sleep in short increments to respond quickly to signals
        sleep_seconds = config.interval_hours * 3600
        start_wait = time.time()
        while running and (time.time() - start_wait < sleep_seconds):
            time.sleep(1)

    logger.info("Daemon stopped.")


def main():
    parser = argparse.ArgumentParser(
        description="Tamriel Trade Centre (TTC) Price Table Auto-Sync for Elder Scrolls Online (Cross-Platform: Linux, Windows, macOS)",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument("--sync", "--once", action="store_true", help="Download & update price table immediately once and exit.")
    parser.add_argument("--status", action="store_true", help="Show current installation, addon paths, file age, and scheduler status.")
    parser.add_argument("--daemon", action="store_true", help="Run in continuous background loop (every --interval hours).")
    parser.add_argument("--install-service", action="store_true", help="Install automated OS scheduler (systemd timer on Linux, Task Scheduler on Windows, launchd on macOS).")
    parser.add_argument("--uninstall-service", action="store_true", help="Remove automated OS scheduler.")
    parser.add_argument("--server", choices=["eu", "na", "both"], help="Select TTC megaserver (eu, na, or both). Default: eu.")
    parser.add_argument("--path", type=str, help="Specify custom path to ESO TamrielTradeCentre folder.")
    parser.add_argument("--interval", type=int, help=f"Set sync interval in hours (default: {DEFAULT_INTERVAL_HOURS}).")
    parser.add_argument("--log-file", type=str, default="ttc_sync.log", help="Path to write log records (default: ttc_sync.log).")

    args = parser.parse_args()
    config = Config()

    # Apply CLI overrides and persist them
    if args.server:
        config.server = args.server
    if args.interval:
        config.interval_hours = args.interval
    if args.path:
        config.target_dir = Path(args.path)

    log_path = Path(args.log_file).resolve()
    logger = setup_logger(log_path)

    # Dispatch commands
    if args.status:
        show_status(config)
        return

    if args.install_service:
        print_banner()
        cprint(f"\nInstalling automatic OS background scheduler (every {config.interval_hours} hours)...", Colors.CYAN)
        ok, msg = install_scheduler(config.interval_hours)
        if ok:
            cprint(f"[✓] {msg}", Colors.GREEN, bold=True)
            print("\nScheduler status:")
            print(f"  {get_scheduler_status()}")
        else:
            cprint(f"[!] {msg}", Colors.RED, bold=True)
            sys.exit(1)
        return

    if args.uninstall_service:
        print_banner()
        cprint("\nUninstalling automatic OS background scheduler...", Colors.CYAN)
        ok, msg = uninstall_scheduler()
        if ok:
            cprint(f"[✓] {msg}", Colors.GREEN, bold=True)
        else:
            cprint(f"[!] {msg}", Colors.RED, bold=True)
            sys.exit(1)
        return

    if args.daemon:
        print_banner()
        run_daemon(config, logger)
        return

    # If --sync is requested or no flag provided, perform a sync
    print_banner()
    success = execute_sync(config, logger)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
