import unittest
import os
import sys
import json
from unittest.mock import patch

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import smart
from server_utils import stop_server

class TestServer(unittest.TestCase):
    """Test cases for the Smart Card Manager server endpoints."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment variables before running tests."""
        os.environ['SMARTY_ENV'] = 'testing'
        
    def setUp(self):
        """Initialize test client before each test."""
        try:
            smart.app.testing = True
            self.client = smart.app.test_client()
        except Exception as e:
            self.fail(f"Failed to set up test client: {str(e)}")
        
    def tearDown(self):
        """Clean up resources after each test."""
        try:
            stop_server()
        except Exception as e:
            print(f"Warning: Exception during tearDown: {str(e)}")
        
    def test_index_page(self):
        """Test that the index page loads correctly."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200, "Index page should return 200 status")
        self.assertIn(b'Smart Card Manager', response.data, "Index page should contain title")
        
    def test_index_page_head_method(self):
        """Test HEAD request to index page."""
        response = self.client.head('/')
        self.assertEqual(response.status_code, 200, "HEAD request should be supported")
        
    def test_server_start_stop(self):
        """Test server start/stop functionality."""
        # Start server
        response = self.client.post('/start_server')
        self.assertEqual(response.status_code, 200, "Starting server should succeed")
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success', "Response should indicate success")
        
        # Stop server
        response = self.client.post('/stop_server')
        self.assertEqual(response.status_code, 200, "Stopping server should succeed")
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success', "Response should indicate success")
        
    def test_server_start_stop_failures(self):
        """Test handling of server start/stop failures."""
        # Test starting already running server
        self.client.post('/start_server')  # Start first time
        response = self.client.post('/start_server')  # Try to start again
        self.assertEqual(response.status_code, 400, "Starting twice should fail")
        
        self.client.post('/stop_server')  # Stop the server
        
        # Test stopping already stopped server
        response = self.client.post('/stop_server')  # Try to stop again
        self.assertEqual(response.status_code, 400, "Stopping twice should fail")
        
    def test_reader_capabilities(self):
        """Test reader capabilities endpoint."""
        # Test with known reader type
        response = self.client.get('/reader_capabilities?reader_name=CHERRY%20Smart%20Terminal%20ST-1234')
        self.assertEqual(response.status_code, 200, "Known reader should return 200 status")
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success', "Response should indicate success")
        
        # Should include capabilities
        self.assertIn('capabilities', data, "Response should include capabilities object")
        self.assertIn('supports_felica', data['capabilities'], "Capabilities should include FeliCa support")
        
    def test_reader_capabilities_edge_cases(self):
        """Test reader capabilities with edge cases."""
        # Test with unknown reader type
        response = self.client.get('/reader_capabilities?reader_name=UNKNOWN_READER')
        self.assertEqual(response.status_code, 404, "Unknown reader should return 404")
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error', "Response should indicate error")
        self.assertIn('message', data, "Error response should include message")
        
        # Test with missing reader parameter
        response = self.client.get('/reader_capabilities')
        self.assertEqual(response.status_code, 400, "Missing reader parameter should return 400")
        
        # Test with empty reader parameter
        response = self.client.get('/reader_capabilities?reader_name=')
        self.assertEqual(response.status_code, 400, "Empty reader parameter should return 400")
        
    def test_invalid_endpoint(self):
        """Test accessing an invalid endpoint."""
        response = self.client.get('/invalid_endpoint')
        self.assertEqual(response.status_code, 404, "Invalid endpoint should return 404")
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error', "Response should indicate error")
        self.assertIn('message', data, "Error response should include message")
        
    @patch('smart.get_connected_readers')
    def test_reader_list_endpoint(self, mock_get_readers):
        """Test listing connected readers."""
        mock_get_readers.return_value = ['Reader 1', 'Reader 2']
        response = self.client.get('/readers')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['readers']), 2)
        self.assertIn('Reader 1', data['readers'])

if __name__ == '__main__':
    unittest.main()