import unittest
import os
import sys
import json
# Remove unused imports
# import tempfile
# from contextlib import contextmanager

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import smart
# Modify to only import what's used
from server_utils import stop_server

class TestServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Set testing environment
        os.environ['SMARTY_ENV'] = 'testing'
        
    def setUp(self):
        # Create a test client
        smart.app.testing = True
        self.client = smart.app.test_client()
        
    def tearDown(self):
        # Clean up after each test
        stop_server()
        
    def test_index_page(self):
        """Test that the index page loads"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Smart Card Manager', response.data)
        
    def test_server_start_stop(self):
        """Test server start/stop functionality"""
        # Start server - use the endpoint directly through the client
        response = self.client.post('/start_server')
        self.assertEqual(response.status_code, 200)
        
        # Stop server
        response = self.client.post('/stop_server')
        self.assertEqual(response.status_code, 200)
        
    def test_reader_capabilities(self):
        """Test reader capabilities endpoint"""
        # Test with known reader type
        response = self.client.get('/reader_capabilities?reader_name=CHERRY%20Smart%20Terminal%20ST-1234')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        
        # Should include capabilities
        self.assertIn('capabilities', data)
        self.assertIn('supports_felica', data['capabilities'])
        
        # Test with unknown reader type
        response = self.client.get('/reader_capabilities?reader_name=UNKNOWN_READER')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
        self.assertIn('message', data)
        
    def test_invalid_endpoint(self):
        """Test accessing an invalid endpoint"""
        response = self.client.get('/invalid_endpoint')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
        self.assertIn('message', data)

if __name__ == '__main__':
    unittest.main()