# tests/__init__.py

# Make test modules easily importable
__all__ = ['test_analytics', 'test_features', 'test_preprocessing']

# Or it might contain test configuration or setup code
import sys
import os

# Add the src directory to the Python path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
