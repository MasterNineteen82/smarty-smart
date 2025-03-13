"""
Smart Card Manager Test Suite
-----------------------------

This package contains tests for the Smart Card Manager application.
Run tests using either:
- python run_tests.py
- python -m pytest tests/
"""

import os
import unittest

def get_test_suite():
    """Return a test suite containing all tests from the tests directory"""
    loader = unittest.TestLoader()
    start_dir = os.path.dirname(__file__)
    if not os.path.isdir(start_dir):
        raise NotADirectoryError(f"The start directory {start_dir} does not exist or is not a directory.")
    
    try:
        suite = loader.discover(start_dir)
    except Exception as e:
        raise RuntimeError(f"Error discovering tests: {e}")
    
    if suite.countTestCases() == 0:
        raise RuntimeError("No test cases found in the test suite.")
    
    return suite

if __name__ == '__main__':
    try:
        suite = get_test_suite()
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        if not result.wasSuccessful():
            exit(1)
    except Exception as e:
        print(f"Failed to run tests: {e}")
        exit(1)