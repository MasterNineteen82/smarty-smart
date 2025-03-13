import unittest
import os
import sys

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from card_utils import (
    get_reader_timeout, detect_reader_type, toHexString
)

class TestCardUtils(unittest.TestCase):
    def test_reader_detection(self):
        """Test reader type detection"""
        # Test Cherry reader detection
        reader_info = detect_reader_type("CHERRY Smart Terminal ST-1234")
        self.assertEqual(reader_info['type'], "CHERRY_ST")
        
        # Test ACR reader detection
        reader_info = detect_reader_type("ACS ACR122U")
        self.assertEqual(reader_info['type'], "ACR122U")
        
        # Test unknown reader
        reader_info = detect_reader_type("Unknown Reader")
        self.assertEqual(reader_info['type'], "GENERIC")
        
        # Test empty string
        reader_info = detect_reader_type("")
        self.assertEqual(reader_info['type'], "GENERIC")
        
        # Test None input
        reader_info = detect_reader_type(None)
        self.assertEqual(reader_info['type'], "GENERIC")
    
    def test_reader_timeout(self):
        """Test reader timeout settings"""
        # Cherry should have longer timeout
        cherry_timeout = get_reader_timeout("CHERRY Smart Terminal ST-1234")
        acr_timeout = get_reader_timeout("ACS ACR122U")
        
        self.assertGreater(cherry_timeout, acr_timeout, 
                         "Cherry readers should have longer timeouts than ACR122U")
        
        # Generic reader should have default timeout
        generic_timeout = get_reader_timeout("Generic Reader")
        self.assertTrue(generic_timeout > 0, "Default timeout should be positive")
        
        # Test empty string
        empty_timeout = get_reader_timeout("")
        self.assertTrue(empty_timeout > 0, "Default timeout should be positive")
        
        # Test None input
        none_timeout = get_reader_timeout(None)
        self.assertTrue(none_timeout > 0, "Default timeout should be positive")

    def test_hex_conversion(self):
        """Test hex string conversion utility"""
        data = [0x01, 0x02, 0xAB, 0xCD]
        hex_str = toHexString(data)
        self.assertEqual(hex_str, "01 02 AB CD")
        
        # Test empty list
        data = []
        hex_str = toHexString(data)
        self.assertEqual(hex_str, "")
        
        # Test None input
        with self.assertRaises(TypeError):
            toHexString(None)

if __name__ == '__main__':
    unittest.main()