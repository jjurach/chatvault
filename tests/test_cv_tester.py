"""
Unit tests for CV-Tester tool.

Tests the cv_tester.py functionality with mock HTTP responses.
"""

import json
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import chatvault.cv_tester as cv_tester
from chatvault.cv_tester import ChatVaultTester, DEFAULT_CONFIG


class TestChatVaultTester(unittest.TestCase):
    """Test cases for ChatVaultTester class."""

    def setUp(self):
        """Set up test fixtures."""
        self.tester = ChatVaultTester('http://localhost:4000', timeout=5)
        self.test_token = DEFAULT_CONFIG['default_bearer_tokens']['local1']

    @patch.object(ChatVaultTester, 'make_request')
    def test_make_request_get_success(self, mock_make_request):
        """Test successful GET request."""
        mock_make_request.return_value = (200, {'status': 'ok'})

        status, data = self.tester.make_request('/health')

        self.assertEqual(status, 200)
        self.assertEqual(data, {'status': 'ok'})

    @patch.object(ChatVaultTester, 'make_request')
    def test_make_request_post_with_auth(self, mock_make_request):
        """Test POST request with bearer token."""
        mock_make_request.return_value = (200, {'result': 'success'})

        test_data = {'model': 'test', 'messages': []}
        status, data = self.tester.make_request('/v1/chat/completions', 'POST',
                                              data=test_data, bearer_token='test-token')

        self.assertEqual(status, 200)
        self.assertEqual(data, {'result': 'success'})

    @patch.object(ChatVaultTester, 'make_request')
    def test_make_request_json_error(self, mock_make_request):
        """Test handling of invalid JSON responses."""
        mock_make_request.return_value = (200, {'error': 'Invalid JSON response', 'text': 'Invalid response text'})

        status, data = self.tester.make_request('/health')

        self.assertEqual(status, 200)
        self.assertIn('error', data)
        self.assertIn('Invalid JSON response', data['error'])

    @patch.object(ChatVaultTester, 'make_request')
    def test_make_request_connection_error(self, mock_make_request):
        """Test handling of connection errors."""
        mock_make_request.return_value = (500, {'error': 'Request failed: Connection failed'})

        status, data = self.tester.make_request('/health')

        self.assertEqual(status, 500)
        self.assertIn('error', data)
        self.assertIn('Request failed', data['error'])

    def test_test_basic_connectivity_success(self):
        """Test successful basic connectivity test."""
        with patch.object(self.tester, 'make_request') as mock_request:
            # Mock successful responses
            mock_request.side_effect = [
                (200, {'status': 'healthy'}),  # Health check
                (200, {'models': []})  # Models endpoint
            ]

            result = self.tester.test_basic_connectivity(self.test_token)

            self.assertEqual(result['status'], 'PASS')
            self.assertEqual(result['test'], 'basic_connectivity')

    def test_test_basic_connectivity_health_fail(self):
        """Test basic connectivity with health check failure."""
        with patch.object(self.tester, 'make_request') as mock_request:
            mock_request.return_value = (500, {'error': 'Server error'})

            result = self.tester.test_basic_connectivity()

            self.assertEqual(result['status'], 'FAIL')
            self.assertIn('Health check failed', result['error'])

    def test_test_authentication_success(self):
        """Test successful authentication."""
        with patch.object(self.tester, 'make_request') as mock_request:
            mock_request.return_value = (200, {'choices': [{'message': {'content': 'Hello'}}]})

            result = self.tester.test_authentication(self.test_token)

            self.assertEqual(result['status'], 'PASS')
            self.assertIn('Authentication successful', result['message'])

    def test_test_authentication_fail(self):
        """Test failed authentication."""
        with patch.object(self.tester, 'make_request') as mock_request:
            mock_request.return_value = (401, {'error': 'Unauthorized'})

            result = self.tester.test_authentication(self.test_token)

            self.assertEqual(result['status'], 'FAIL')
            self.assertIn('Authentication failed', result['error'])

    def test_test_model_restrictions_success(self):
        """Test successful model restrictions validation."""
        with patch.object(self.tester, 'make_request') as mock_request:
            # Mock all the requests made by test_model_restrictions method
            # 1. local1 access to vault-qwen3-8k (should succeed)
            # 2. local1 access to vault-mistral-nemo-8k (should succeed)
            # 3. full1 access to vault-qwen3-8k (should succeed)
            mock_request.side_effect = [
                (200, {'choices': []}),  # local1 qwen3-8k
                (200, {'choices': []}),  # local1 mistral
                (200, {'choices': []})   # full1 qwen3-8k
            ]

            result = self.tester.test_model_restrictions('restricted-token', 'full-token')

            self.assertEqual(result['status'], 'PASS')
            self.assertEqual(result['local1_qwen3_test'], 'PASS')
            self.assertEqual(result['local1_mistral_test'], 'PASS')
            self.assertEqual(result['full1_qwen3_test'], 'PASS')

    def test_test_streaming_response_success(self):
        """Test successful streaming response."""
        with patch.object(self.tester, 'make_request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {'content-type': 'text/event-stream'}
            mock_response.iter_lines.return_value = [
                b'data: {"choices":[]}',
                b'data: [DONE]'
            ]
            mock_request.return_value = (200, mock_response)

            result = self.tester.test_streaming_response(self.test_token)

            self.assertEqual(result['status'], 'PASS')
            self.assertIn('Streaming response received', result['message'])

    def test_test_streaming_response_wrong_content_type(self):
        """Test streaming response with wrong content type."""
        with patch.object(self.tester, 'make_request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {'content-type': 'application/json'}
            mock_request.return_value = (200, mock_response)

            result = self.tester.test_streaming_response(self.test_token)

            self.assertEqual(result['status'], 'FAIL')
            self.assertIn('Invalid content-type', result['error'])

    def test_test_error_handling_success(self):
        """Test successful error handling validation."""
        with patch.object(self.tester, 'make_request') as mock_request:
            # Mock error responses
            mock_request.side_effect = [
                (400, {'error': 'Bad Request'}),  # Invalid model
                (401, {'error': 'Unauthorized'})  # Missing auth
            ]

            result = self.tester.test_error_handling()

            self.assertEqual(result['status'], 'PASS')
            self.assertEqual(result['error_test'], 'PASS')
            self.assertEqual(result['auth_error_test'], 'PASS')

    def test_run_tests_basic(self):
        """Test running basic test suite."""
        with patch.object(self.tester, 'test_basic_connectivity') as mock_test:
            mock_test.return_value = {'status': 'PASS', 'test': 'basic_connectivity'}

            results = self.tester.run_tests(['basic'])

            self.assertEqual(results['summary']['total'], 1)
            self.assertEqual(results['summary']['passed'], 1)
            self.assertEqual(results['summary']['failed'], 0)
            self.assertEqual(len(results['tests_run']), 1)

    def test_run_tests_multiple(self):
        """Test running multiple test types."""
        with patch.object(self.tester, 'test_basic_connectivity') as mock_basic, \
             patch.object(self.tester, 'test_authentication') as mock_auth, \
             patch.object(self.tester, 'test_model_restrictions') as mock_restrictions:

            mock_basic.return_value = {'status': 'PASS', 'test': 'basic_connectivity'}
            mock_auth.return_value = {'status': 'FAIL', 'test': 'authentication'}
            mock_restrictions.return_value = {'status': 'PASS', 'test': 'model_restrictions'}

            results = self.tester.run_tests(['basic', 'models'])

            self.assertEqual(results['summary']['total'], 3)
            self.assertEqual(results['summary']['passed'], 2)
            self.assertEqual(results['summary']['failed'], 1)


class TestCommandLineInterface(unittest.TestCase):
    """Test cases for command-line interface."""

    @patch('chatvault.cv_tester.ChatVaultTester')
    def test_main_basic_args(self, mock_tester_class):
        """Test main function with basic arguments."""
        mock_tester = Mock()
        mock_tester.run_tests.return_value = {
            'summary': {'total': 1, 'passed': 1, 'failed': 0},
            'tests_run': [{'status': 'PASS', 'test': 'basic'}]
        }
        mock_tester_class.return_value = mock_tester

        with patch('sys.argv', ['cv_tester.py', 'basic']):
            with patch('builtins.print') as mock_print:
                from chatvault.cv_tester import main
                main()

                # Verify tester was created with correct URL
                mock_tester_class.assert_called_with('http://localhost:4000', 30)

                # Verify tests were run
                mock_tester.run_tests.assert_called_once()

    @patch('chatvault.cv_tester.ChatVaultTester')
    def test_main_with_port_override(self, mock_tester_class):
        """Test main function with port override."""
        mock_tester = Mock()
        mock_tester.run_tests.return_value = {
            'summary': {'total': 1, 'passed': 1, 'failed': 0},
            'tests_run': []
        }
        mock_tester_class.return_value = mock_tester

        with patch('sys.argv', ['cv_tester.py', '--port', '8080', 'basic']):
            with patch('builtins.print'):
                from chatvault.cv_tester import main
                main()

                # Verify tester was created with modified URL
                mock_tester_class.assert_called_with('http://localhost:8080', 30)

    @patch('chatvault.cv_tester.ChatVaultTester')
    def test_main_with_bearer_token(self, mock_tester_class):
        """Test main function with custom bearer token."""
        mock_tester = Mock()
        mock_tester.run_tests.return_value = {
            'summary': {'total': 1, 'passed': 1, 'failed': 0},
            'tests_run': []
        }
        mock_tester_class.return_value = mock_tester

        test_token = 'custom-token-123'
        with patch('sys.argv', ['cv_tester.py', '--bearer', test_token, 'basic']):
            with patch('builtins.print'):
                from chatvault.cv_tester import main
                main()

                # Verify tests were run with custom token
                mock_tester.run_tests.assert_called_once()
                args, kwargs = mock_tester.run_tests.call_args
                self.assertEqual(args[1], test_token)

    @patch('chatvault.cv_tester.ChatVaultTester')
    def test_main_json_output(self, mock_tester_class):
        """Test main function with JSON output."""
        mock_tester = Mock()
        test_results = {
            'summary': {'total': 1, 'passed': 1, 'failed': 0},
            'tests_run': [{'status': 'PASS', 'test': 'basic'}],
            'timestamp': 1234567890
        }
        mock_tester.run_tests.return_value = test_results
        mock_tester_class.return_value = mock_tester

        with patch('sys.argv', ['cv_tester.py', '--json', 'basic']):
            with patch('json.dumps') as mock_dumps, \
                 patch('builtins.print') as mock_print:

                mock_dumps.return_value = '{"test": "data"}'

                from chatvault.cv_tester import main
                main()

                # Verify JSON output was used
                mock_dumps.assert_called_once_with(test_results, indent=2)
                mock_print.assert_called_once_with('{"test": "data"}')


if __name__ == '__main__':
    unittest.main()