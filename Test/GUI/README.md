# GUI Tests

This directory contains tests for the GUI components of the StreamingCommunity application.

## Test Files

- `test_main_window.py`: Tests for the main window class (`StreamingGUI`)
- `test_run_tab.py`: Tests for the run tab component (`RunTab`)
- `test_results_table.py`: Tests for the results table widget (`ResultsTable`)
- `test_stream_redirect.py`: Tests for the stdout redirection utility (`Stream`)
- `test_site_manager.py`: Tests for the site manager utility
- `test_integration.py`: Integration tests for all GUI components working together

## Running the Tests

### Using the Test Runner

The easiest way to run the tests is to use the included test runner script:

```bash
# Run all tests
cd Test/GUI
python run_tests.py

# Run specific test files
python run_tests.py test_main_window.py test_run_tab.py

# Run with different verbosity level (1-3)
python run_tests.py -v 3
```

### Using unittest Directly

You can also run the tests using the standard unittest module:

```bash
# Run all GUI tests
python -m unittest discover -s Test/GUI

# Run individual test files
python -m unittest Test/GUI/test_main_window.py
python -m unittest Test/GUI/test_run_tab.py
python -m unittest Test/GUI/test_results_table.py
python -m unittest Test/GUI/test_stream_redirect.py
python -m unittest Test/GUI/test_site_manager.py
python -m unittest Test/GUI/test_integration.py
```

## Test Coverage

The tests cover the following aspects of the GUI:

1. **Basic Initialization**
   - Proper initialization of all GUI components
   - Correct parent-child relationships
   - Default states of widgets

2. **UI Creation**
   - Correct creation of all UI elements
   - Proper layout of widgets
   - Initial visibility states

3. **Widget Interactions**
   - Button clicks
   - Checkbox toggles
   - Table updates

4. **Process Execution**
   - Script execution
   - Process termination
   - Status updates

5. **Integration**
   - Components working together correctly
   - Signal-slot connections
   - Data flow between components

## Adding New Tests

When adding new GUI components, please add corresponding tests following the same pattern as the existing tests. Each test file should:

1. Import the necessary modules
2. Create a test class that inherits from `unittest.TestCase`
3. Include setup and teardown methods
4. Test all aspects of the component's functionality
5. Include a main block to run the tests when the file is executed directly

## Notes

- The tests use `unittest.mock` to mock external dependencies like `QProcess`
- A `QApplication` instance is created in the `setUpClass` method to ensure that PyQt widgets can be created
- The tests clean up resources in the `tearDown` method to prevent memory leaks
