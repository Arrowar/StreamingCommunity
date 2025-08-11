
import os
import sys
import unittest
import logging


# Fix path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(src_path)


from StreamingCommunity.global_search import load_search_functions

class TestLoadSearchFunctions(unittest.TestCase):
    def test_load_search_functions_no_exceptions(self):
        try:
            logging.basicConfig(level=logging.INFO)
            
            # Call the function to be tested
            loaded_functions = load_search_functions()
            
            # Verify that at least some modules were loaded
            self.assertTrue(len(loaded_functions) > 0, "No modules were loaded")
            
            # Print successfully loaded modules
            print("\nSuccessfully loaded modules:")
            for module_name, (_, use_for) in loaded_functions.items():
                print(f"- {module_name} (type: {use_for})")
            
            print(f"\nTotal modules loaded: {len(loaded_functions)}")
            
        except Exception as e:
            self.fail(f"Error during module loading: {str(e)}")

if __name__ == '__main__':
    unittest.main()