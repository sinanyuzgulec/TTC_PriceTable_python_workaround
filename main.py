#!/usr/bin/env python3
"""
Tamriel Trade Centre (TTC) Price Table Auto-Sync
Entrypoint script.
"""

import sys
from pathlib import Path

# Add project root to sys.path so ttc_sync can be imported directly
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from ttc_sync.cli import main

if __name__ == "__main__":
    main()
