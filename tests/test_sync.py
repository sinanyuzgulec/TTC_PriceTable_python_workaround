"""
Unit and integration tests for TTC Price Table Sync.
"""

import io
import zipfile
import tempfile
import unittest
from pathlib import Path

from ttc_sync.detector import get_candidate_addon_directories, get_platform_name
from ttc_sync.config import Config
from ttc_sync.downloader import extract_zip_safely, DownloadError


class TestDetector(unittest.TestCase):
    def test_candidates_returned(self):
        candidates = get_candidate_addon_directories()
        self.assertIsInstance(candidates, list)
        self.assertGreater(len(candidates), 0)

    def test_platform_name(self):
        plat = get_platform_name()
        self.assertIn(plat, ["linux", "windows", "darwin"])


class TestConfig(unittest.TestCase):
    def test_config_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_file = Path(tmpdir) / "test_config.json"
            cfg = Config(config_file=cfg_file)

            # Test defaults
            self.assertEqual(cfg.server, "eu")
            self.assertEqual(cfg.interval_hours, 12)

            # Modify and save
            cfg.server = "na"
            cfg.interval_hours = 6
            cfg.record_sync_success(["PriceTableNA.lua"], 12345)

            # Reload
            cfg2 = Config(config_file=cfg_file)
            self.assertEqual(cfg2.server, "na")
            self.assertEqual(cfg2.interval_hours, 6)
            self.assertEqual(cfg2.data["last_sync_status"], "success")
            self.assertEqual(cfg2.data["last_sync_bytes"], 12345)


class TestDownloader(unittest.TestCase):
    def test_extract_zip_safely(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir) / "TamrielTradeCentre"

            # Create mock zip archive
            bio = io.BytesIO()
            with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("PriceTableEU.lua", 'PriceTable = { ["test"] = 100 }')
                zf.writestr("ItemLookUpTable_EN.lua", 'ItemLookUp = { ["test"] = 1 }')

            zip_bytes = bio.getvalue()
            extracted = extract_zip_safely(zip_bytes, target_dir)

            self.assertIn("PriceTableEU.lua", extracted)
            self.assertIn("ItemLookUpTable_EN.lua", extracted)
            self.assertTrue((target_dir / "PriceTableEU.lua").is_file())
            self.assertEqual((target_dir / "PriceTableEU.lua").read_text(), 'PriceTable = { ["test"] = 100 }')

    def test_extract_zip_blocks_non_lua_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir) / "TamrielTradeCentre"

            bio = io.BytesIO()
            with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("PriceTableEU.lua", 'PriceTable = {}')
                zf.writestr("malicious.exe", 'binary data')
                zf.writestr("script.sh", '#!/bin/sh\nrm -rf /')
                zf.writestr("config.json", '{"key": "value"}')

            zip_bytes = bio.getvalue()
            extracted = extract_zip_safely(zip_bytes, target_dir)

            self.assertIn("PriceTableEU.lua", extracted)
            self.assertNotIn("malicious.exe", extracted)
            self.assertNotIn("script.sh", extracted)
            self.assertNotIn("config.json", extracted)

            # Assert only lua exists on disk
            self.assertTrue((target_dir / "PriceTableEU.lua").exists())
            self.assertFalse((target_dir / "malicious.exe").exists())
            self.assertFalse((target_dir / "script.sh").exists())
            self.assertFalse((target_dir / "config.json").exists())

    def test_extract_empty_or_invalid_zip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            with self.assertRaises(DownloadError):
                extract_zip_safely(b"not a zip file", target_dir)

            with self.assertRaises(DownloadError):
                extract_zip_safely(b"<html>404 Not Found</html>", target_dir)


if __name__ == "__main__":
    unittest.main()
