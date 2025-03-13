#!/usr/bin/env python3
"""
Test runner for Smart Card Manager
Runs all tests and reports results
"""

import unittest
import sys
import os
from contextlib import contextmanager
import argparse

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

    for module_name in test_modules:
        try:
            # Import test module
            __import__(module_name)
            module = sys.modules[module_name]

            # Add tests from module
            module_tests = test_loader.loadTestsFromModule(module)
            test_suite.addTests(module_tests)
        except (ImportError, AttributeError) as e:
            print(f"Error loading test module {module_name}: {e}")

    if test_suite.countTestCases() == 0:
        print("No tests found in the test modules.")
        return False

    # Run tests
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)

    return result.wasSuccessful()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run Smart Card Manager tests')
    parser.add_argument('--capture', action='store_true', help='Capture output for web display')
    args = parser.parse_args()

    if args.capture:
        print("Running Smart Card Manager tests...\n")
        with suppress_stdout():
            success = run_tests()
        print("\nSummary:", "PASSED" if success else "FAILED")
        sys.exit(0 if success else 1)
    else:
        print("Running Smart Card Manager tests...")
        success = run_tests()
        sys.exit(0 if success else 1)