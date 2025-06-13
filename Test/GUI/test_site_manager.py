# Fix import
import sys
import os
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(src_path)

# Import
import unittest
from unittest.mock import patch, MagicMock

from gui.utils.site_manager import get_sites, sites

class TestSiteManager(unittest.TestCase):
    @patch('gui.utils.site_manager.load_search_functions')
    def test_get_sites(self, mock_load_search_functions):
        """Test that the get_sites function correctly processes search functions"""
        # Set up the mock to return a dictionary of search functions
        mock_load_search_functions.return_value = {
            'site1_search': (MagicMock(), 'movie'),
            'site2_search': (MagicMock(), 'tv'),
            'site3_search': (MagicMock(), 'anime'),
        }
        
        # Call the function
        result = get_sites()
        
        # Check that the mock was called
        mock_load_search_functions.assert_called_once()
        
        # Check that the result is a list
        self.assertIsInstance(result, list)
        
        # Check that the result has the correct length
        self.assertEqual(len(result), 3)
        
        # Check that each item in the result is a dictionary with the correct keys
        for i, site in enumerate(result):
            self.assertIsInstance(site, dict)
            self.assertIn('index', site)
            self.assertIn('name', site)
            self.assertIn('flag', site)
            
            # Check that the index is correct
            self.assertEqual(site['index'], i)
            
            # Check that the name is correct (the part before '_' in the key)
            expected_name = f'site{i+1}'
            self.assertEqual(site['name'], expected_name)
            
            # Check that the flag is correct (first 3 characters of the key, uppercase)
            expected_flag = f'SIT'
            self.assertEqual(site['flag'], expected_flag)
    
    def test_sites_variable(self):
        """Test that the sites variable is a list"""
        # Check that sites is a list
        self.assertIsInstance(sites, list)
        
        # Check that each item in sites is a dictionary with the correct keys
        for site in sites:
            self.assertIsInstance(site, dict)
            self.assertIn('index', site)
            self.assertIn('name', site)
            self.assertIn('flag', site)

if __name__ == '__main__':
    unittest.main()