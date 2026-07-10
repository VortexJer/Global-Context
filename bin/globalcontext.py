#!/usr/bin/env python3
"""Global Context CLI entry point."""
import sys
from pathlib import Path

# Add the source tree next to this script to the path
script_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(script_dir.parent))

from globalcontext.cli import main

if __name__ == "__main__":
    main()
