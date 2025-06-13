#!/usr/bin/env python3

# Fix import
import sys
import os
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(src_path)

# Import
import unittest
import argparse

def run_tests(verbosity=2, test_names=None):
    """Run the GUI tests with the specified verbosity level."""
    # Create a test loader
    loader = unittest.TestLoader()
    
    # If specific test names are provided, run only those tests
    if test_names:
        suite = unittest.TestSuite()
        for test_name in test_names:
            # Try to load the test module
            try:
                if test_name.endswith('.py'):
                    test_name = test_name[:-3]  # Remove .py extension
                
                # If the test name is a module name, load all tests from that module
                if test_name.startswith('test_'):
                    module = __import__(test_name)
                    suite.addTests(loader.loadTestsFromModule(module))
                else:
                    # Otherwise, assume it's a test class or method name
                    suite.addTests(loader.loadTestsFromName(test_name))
            except (ImportError, AttributeError) as e:
                print(f"Error loading test {test_name}: {e}")
                return False
    else:
        # Otherwise, discover all tests in the current directory
        suite = loader.discover('.', pattern='test_*.py')
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    # Return True if all tests passed, False otherwise
    return result.wasSuccessful()

if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run GUI tests for StreamingCommunity')
    parser.add_argument('-v', '--verbosity', type=int, default=2,
                        help='Verbosity level (1-3, default: 2)')
    parser.add_argument('test_names', nargs='*',
                        help='Specific test modules, classes, or methods to run')
    args = parser.parse_args()
    
    # Run the tests
    success = run_tests(args.verbosity, args.test_names)
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)