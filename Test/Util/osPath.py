
import os
import sys
import unittest
from unittest.mock import patch


# Fix path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(src_path)


from StreamingCommunity.Util.os import OsManager

class TestOsManager(unittest.TestCase):
    def setUp(self):
        self.test_paths = {
            'windows': {
                'network': [
                    (r'\\server\share\folder\file.txt', r'\\server\share\folder\file.txt'),
                    (r'\\192.168.1.100\share\folder\file.txt', r'\\192.168.1.100\share\folder\file.txt'),
                    (r'\\server\share', r'\\server\share'),
                    (r'\\server\share\\folder//subfolder\file.txt', r'\\server\share\folder\subfolder\file.txt')
                ],
                'drive': [
                    ('C:\\folder\\file.txt', 'C:\\folder\\file.txt'),
                    ('C:/folder/file.txt', 'C:\\folder\\file.txt'),
                    ('D:\\Test\\file.txt', 'D:\\Test\\file.txt'),
                    ('D:/Test/file.txt', 'D:\\Test\\file.txt')
                ],
                'relative': [
                    ('folder\\file.txt', 'folder\\file.txt'),
                    ('folder/file.txt', 'folder\\file.txt'),
                    ('.\\folder\\file.txt', 'folder\\file.txt')
                ]
            },
            'darwin': {
                'absolute': [
                    ('/media/TV/show.mp4', '/media/TV/show.mp4'),
                    ('/Users/name/Documents/file.txt', '/Users/name/Documents/file.txt'),
                    ('/media/TV/show.mp4', '/media/TV/show.mp4')
                ],
                'relative': [
                    ('folder/file.txt', 'folder/file.txt'),
                    ('folder/file.txt', 'folder/file.txt')
                ]
            },
            'linux': {
                'absolute': [
                    ('/home/user/file.txt', '/home/user/file.txt'),
                    ('/mnt/data/file.txt', '/mnt/data/file.txt'),
                    ('/home/user/file.txt', '/home/user/file.txt')
                ],
                'relative': [
                    ('folder/file.txt', 'folder/file.txt'),
                    ('folder/file.txt', 'folder/file.txt')
                ]
            }
        }

    def test_sanitize_file(self):
        with patch('platform.system', return_value='Windows'):
            manager = OsManager()
            test_cases = [
                ('file.txt', 'file.txt'),
                ('filéš.txt', 'files.txt')
            ]
            for input_name, expected in test_cases:
                with self.subTest(input_name=input_name):
                    result = manager.get_sanitize_file(input_name)
                    self.assertEqual(result, expected)

    def test_windows_paths(self):
        with patch('platform.system', return_value='Windows'):
            manager = OsManager()
            
            # Test network paths (including IP)
            for input_path, expected in self.test_paths['windows']['network']:
                with self.subTest(input_path=input_path):
                    result = manager.get_sanitize_path(input_path)
                    self.assertEqual(result, expected)
            
            # Test drive paths
            for input_path, expected in self.test_paths['windows']['drive']:
                with self.subTest(input_path=input_path):
                    result = manager.get_sanitize_path(input_path)
                    self.assertEqual(result, expected)

    def test_macos_paths(self):
        with patch('platform.system', return_value='Darwin'):
            manager = OsManager()
            
            # Test absolute paths
            for input_path, expected in self.test_paths['darwin']['absolute']:
                with self.subTest(input_path=input_path):
                    result = manager.get_sanitize_path(input_path)
                    self.assertEqual(result, expected)
            
            # Test relative paths
            for input_path, expected in self.test_paths['darwin']['relative']:
                with self.subTest(input_path=input_path):
                    result = manager.get_sanitize_path(input_path)
                    self.assertEqual(result, expected)

    def test_linux_paths(self):
        with patch('platform.system', return_value='Linux'):
            manager = OsManager()
            
            for input_path, expected in self.test_paths['linux']['absolute']:
                with self.subTest(input_path=input_path):
                    result = manager.get_sanitize_path(input_path)
                    self.assertEqual(result, expected)

    def test_special_characters(self):
        with patch('platform.system', return_value='Windows'):
            manager = OsManager()
            special_cases = [
                ('\\\\server\\share\\àèìòù\\file.txt', '\\\\server\\share\\aeiou\\file.txt'),
                ('D:\\Test\\åäö\\file.txt', 'D:\\Test\\aao\\file.txt'),
                ('\\\\192.168.1.100\\share\\tést\\file.txt', '\\\\192.168.1.100\\share\\test\\file.txt')
            ]
            
            for input_path, expected in special_cases:
                with self.subTest(input_path=input_path):
                    result = manager.get_sanitize_path(input_path)
                    self.assertEqual(result, expected)

    def test_network_paths_with_ip(self):
        with patch('platform.system', return_value='Windows'):
            manager = OsManager()
            ip_paths = [
                ('\\\\192.168.1.100\\share\\folder', '\\\\192.168.1.100\\share\\folder'),
                ('\\\\10.0.0.50\\public\\data.txt', '\\\\10.0.0.50\\public\\data.txt'),
                ('\\\\172.16.254.1\\backup\\test.txt', '\\\\172.16.254.1\\backup\\test.txt'),
                ('\\\\192.168.1.100\\share\\folder\\sub dir\\file.txt', 
                 '\\\\192.168.1.100\\share\\folder\\sub dir\\file.txt'),
            ]
            
            for input_path, expected in ip_paths:
                with self.subTest(input_path=input_path):
                    result = manager.get_sanitize_path(input_path)
                    self.assertEqual(result, expected)

if __name__ == '__main__':
    unittest.main()