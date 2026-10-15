"""
Downloader module for Tamriel Trade Centre (TTC) PriceTable data.
Downloads, verifies, and safely unpacks the price tables into the target addon folder.
"""

import io
import os
import sys
import time
import zipfile
import tempfile
import urllib.request
import urllib.error
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Callable


TTC_URLS = {
    "eu": "https://eu.tamrieltradecentre.com/download/PriceTable",
    "na": "https://us.tamrieltradecentre.com/download/PriceTable",
}

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 (TTC_PriceTable_Workaround)"


class DownloadError(Exception):
    pass


def download_zip_data(url: str, retries: int = 3, timeout: int = 30, log_fn: Optional[Callable[[str], None]] = None) -> bytes:
    """
    Download zip content from URL with retry mechanism and exponential backoff.
    """
    def log(msg: str):
        if log_fn:
            log_fn(msg)

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/zip,application/octet-stream,*/*",
            "Accept-Encoding": "identity",
            "Connection": "close",
        }
    )

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            log(f"Downloading price data from {url} (attempt {attempt}/{retries})...")
            start_t = time.time()
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status != 200:
                    raise DownloadError(f"HTTP {resp.status} received from {url}")
                data = resp.read()
                elapsed = time.time() - start_t
                log(f"Downloaded {len(data):,} bytes in {elapsed:.2f}s")
                return data
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
            last_err = e
            log(f"Attempt {attempt} failed: {e}")
            if attempt < retries:
                sleep_time = attempt * 2
                log(f"Waiting {sleep_time}s before retrying...")
                time.sleep(sleep_time)

    raise DownloadError(f"Failed to download from {url} after {retries} attempts: {last_err}")


def extract_zip_safely(zip_data: bytes, target_dir: Path, log_fn: Optional[Callable[[str], None]] = None) -> List[str]:
    """
    Extract zip files atomically and safely into target_dir.
    Returns list of extracted file names.
    """
    def log(msg: str):
        if log_fn:
            log_fn(msg)

    target_dir.mkdir(parents=True, exist_ok=True)

    # Verify zip magic bytes (starts with PK\x03\x04 or PK\x05\x06)
    if not (zip_data.startswith(b"PK\x03\x04") or zip_data.startswith(b"PK\x05\x06")):
        raise DownloadError("Downloaded file is not a valid zip archive (invalid magic bytes). Only ZIP files are allowed.")

    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_data))
    except zipfile.BadZipFile as e:
        raise DownloadError(f"Downloaded file is not a valid zip archive: {e}")

    file_list = zf.namelist()
    if not file_list:
        raise DownloadError("Zip archive is empty!")

    # Verify that expected lua files are in the archive
    has_lua = any(f.lower().endswith(".lua") for f in file_list)
    if not has_lua:
        raise DownloadError(f"Zip archive does not contain expected .lua files: {file_list}")

    extracted_files = []
    blocked_files = []

    # Strict whitelist: ONLY .lua files are permitted to be extracted!
    # Any other extension (e.g. .exe, .dll, .bat, .sh, .bin) is strictly blocked.
    for filename in file_list:
        safe_name = os.path.basename(filename)
        if not safe_name:
            continue

        # Security check: only allow .lua files
        if not safe_name.lower().endswith(".lua"):
            blocked_files.append(safe_name)
            continue

        dest_path = target_dir / safe_name
        tmp_path = target_dir / f".{safe_name}.tmp_{int(time.time())}"

        data = zf.read(filename)
        with open(tmp_path, "wb") as f:
            f.write(data)

        # Atomic rename / replace
        if dest_path.exists():
            dest_path.unlink()
        tmp_path.rename(dest_path)

        extracted_files.append(safe_name)

    if blocked_files:
        log(f"[Security] Blocked non-lua files from archive: {', '.join(blocked_files)}")

    log(f"Successfully extracted {len(extracted_files)} Lua files: {', '.join(extracted_files)}")
    return extracted_files


def sync_price_table(target_dir: Path, server: str = "eu", log_fn: Optional[Callable[[str], None]] = None) -> Tuple[List[str], int]:
    """
    Perform full sync for specified server(s): 'eu', 'na', or 'both'.
    Returns (list of updated file names, total bytes downloaded).
    """
    def log(msg: str):
        if log_fn:
            log_fn(msg)

    servers_to_fetch = ["eu", "na"] if server.lower() == "both" else [server.lower()]
    all_files = []
    total_bytes = 0

    for s in servers_to_fetch:
        if s not in TTC_URLS:
            log(f"[Warning] Unknown server '{s}', skipping.")
            continue

        url = TTC_URLS[s]
        log(f"--- Starting Sync for server [{s.upper()}] ---")
        zip_data = download_zip_data(url, log_fn=log_fn)
        total_bytes += len(zip_data)
        files = extract_zip_safely(zip_data, target_dir, log_fn=log_fn)
        all_files.extend(files)

    # Deduplicate extracted file list
    return list(dict.fromkeys(all_files)), total_bytes
