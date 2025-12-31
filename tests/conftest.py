https://github.com/Queenbih87/ton-assets/blob/coderabbitai%2Futg%2F829c8fc/tests%2Fconftest.py"""
Pytest configuration and shared fixtures for the test suite
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))