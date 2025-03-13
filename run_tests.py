# filepath: x:\smarty-smart\run_tests.py
"""
Test runner for Smart Card Manager
Runs all tests and reports results
"""

import unittest
import sys
import os
from contextlib import contextmanager
import argparse
import subprocess
import logging
import traceback  # Import traceback for detailed error logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

@contextmanager
def suppress_stdout():
    """Temporarily suppress stdout output"""
    stdout = sys.stdout
    try:
        with open(os.devnull, 'w') as devnull:
            sys.stdout = devnull
            yield
    finally:
        sys.stdout = stdout

def run_tests():
    """Run all tests and return True if all tests pass"""
    try:
        # Find all test modules in the tests directory
        test_dir = os.path.join(os.path.dirname(__file__), 'tests')
        if not os.path.isdir(test_dir):
            logging.error(f"Test directory '{test_dir}' does not exist.")
            return False

        test_modules = []
        for file in os.listdir(test_dir):
            if file.startswith('test_') and file.endswith('.py'):
                module_name = file[:-3]  # Remove .py extension
                test_modules.append(f'tests.{module_name}')

        if not test_modules:
            logging.warning("No test modules found.")
            return False

        # Create test suite
        test_loader = unittest.TestLoader()
        test_suite = unittest.TestSuite()

        for module in test_modules:
            try:
                test_suite.addTest(test_loader.loadTestsFromName(module))
            except Exception as e:
                logging.error(f"Error loading tests from module '{module}': {e}")
                logging.error(traceback.format_exc())  # Log detailed traceback
                return False

        # Run tests
        with suppress_stdout():
            runner = unittest.TextTestRunner(verbosity=2)
            result = runner.run(test_suite)

        if not result.wasSuccessful():
            logging.error("Some tests failed during execution.")

        # Run log analysis
        try:
            logging.info("Running log analysis...")
            subprocess.run(["python", "tests/logreview.py"], check=True, capture_output=True, text=True)  # Capture output for logging
            logging.info("Log analysis completed.")
        except subprocess.CalledProcessError as e:
            logging.error(f"Log analysis failed: {e}")
            logging.error(f"Log analysis output: {e.output}")  # Log the output of the failed process
            return False

        # Return True if all tests pass
        return result.wasSuccessful()

    except Exception as e:
        logging.critical(f"An unexpected error occurred: {e}")
        logging.critical(traceback.format_exc())  # Log detailed traceback
        return False

if __name__ == "__main__":
    try:
        if run_tests():
            print("All tests passed.")
            sys.exit(0)
        else:
            print("Some tests failed.")
            sys.exit(1)
    except Exception as e:
        logging.critical(f"An unhandled error occurred in main: {e}")
        logging.critical(traceback.format_exc())
        sys.exit(1)