#!/usr/bin/env python3
"""
Master Test Runner for Confluence PRD Converter.
"""

import unittest
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.discover(str(Path(__file__).parent), pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
