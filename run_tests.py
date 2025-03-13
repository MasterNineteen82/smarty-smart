"""
Test runner for Smart Card Manager
Runs all tests and reports results
"""

import unittest
import sys
import os
from contextlib import contextmanager
import argparse
import subprocess  # Import the subprocess module
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

@contextmanager
def suppress_stdout():
    """Temporarily suppress stdout output"""
    stdout = sys.stdout
    with open(os.devnull, 'w') as devnull:
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = stdout

def run_tests():
    """Run all tests and return True if all tests pass"""
    # Find all test modules in the tests directory
    test_dir = os.path.join(os.path.dirname(__file__), 'tests')
    if not os.path.isdir(test_dir):
        print(f"Test directory '{test_dir}' does not exist.")
        return False

    test_modules = []
    for file in os.listdir(test_dir):
        if file.startswith('test_') and file.endswith('.py'):
            module_name = file[:-3]  # Remove .py extension
            test_modules.append(f'tests.{module_name}')

    if not test_modules:
        print("No test modules found.")
        return False

    # Create test suite
    test_loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()

    for module in test_modules:
        try:
            test_suite.addTest(test_loader.loadTestsFromName(module))
        except Exception as e:
            print(f"Error loading tests from module '{module}': {e}")
            return False

    # Run tests
    with suppress_stdout():
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(test_suite)

    # Run log analysis
    try:
        logging.info("Running log analysis...")
        subprocess.run(["python", "tests/logreview.py"], check=True)  # Execute logreview.py
        logging.info("Log analysis completed.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Log analysis failed: {e}")
        return False

    # Return True if all tests pass
    return result.wasSuccessful()

if __name__ == "__main__":
    if run_tests():
        print("All tests passed.")
        sys.exit(0)
    else:
        print("Some tests failed.")
        sys.exit(1)