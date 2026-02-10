#!/usr/bin/env python3
import sys
import os

# Add src to sys.path so we can import gmail_manager regardless of CWD context
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from gmail_manager.gui import run

if __name__ == "__main__":
    run()
