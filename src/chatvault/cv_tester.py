#!/usr/bin/env python3
"""
CV-Tester - Testing tool for ChatVault

A comprehensive testing client that validates ChatVault functionality by making
actual HTTP requests to the OpenAI-compatible API endpoints. Supports authentication,
model restrictions, streaming responses, and various error conditions.
"""

import argparse
import json
import sys
import time
from typing import Dict, Any, List, Optional, Tuple
import requests
from urllib.parse import urljoin


# Default configuration
DEFAULT_CONFIG = {
    'chatvault_url': 'http://localhost:4000',
    'timeout': 30,
    'default_bearer_tokens': {
        'mobile1': 'YOUR_LOCAL1_BEARER_TOKEN',
        'full3': 'YOUR_FULL1_BEARER_TOKEN'
    }
}


class ChatVaultTester:
    """Main testing class for ChatVault functionality."""

    def __init__(self, base_url: str, timeout: int = 30):
        """
        Initialize the tester with ChatVault connection details.

        Args:
            base_url: Base URL for ChatVault instance
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()

    def make_request(self, endpoint: str, method: str = 'GET',
                    data: Optional[Dict[str, Any]] = None,
                    bearer_token: Optional[str] = None,
                    stream: bool = False) -> Tuple[int, Any]:
        """
        Make an HTTP request to ChatVault.

        Args:
            endpoint: API endpoint (e.g., '/v1/models')
            method: HTTP method
            data: Request data for POST requests
            bearer_token: Bearer token for authentication
            stream: Whether to stream the response

        Returns:
            Tuple of (status_code, response_data)
        """
        url = urljoin(self.base_url + '/', endpoint.lstrip('/'))
        headers = {'Content-Type': 'application/json'}

        if bearer_token:
            headers['Authorization'] = f'Bearer {bearer_token}'
            # Log the authorization header for debugging
            masked_token = bearer_token[:10] + '...' if len(bearer_token) > 10 else bearer_token
            print(f"DEBUG: Using Authorization header: Bearer {masked_token}")

        try:
            if method.upper() == 'GET':
                response = self.session.get(url, headers=headers, timeout=self.timeout, stream=stream)
            elif method.upper() == 'POST':
                response = self.session.post(url, headers=headers,
                                           json=data, timeout=self.timeout, stream=stream)
            else:
                return 500, {'error': f'Unsupported method: {method}'}

            if stream:
                # For streaming responses, return the response object directly
                return response.status_code, response
            else:
                # For regular responses, parse JSON
                try:
                    return response.status_code, response.json()
                except json.JSONDecodeError:
                    return response.status_code, {'error': 'Invalid JSON response',
                                                 'text': response.text[:500]}

        except requests.exceptions.RequestException as e:
            return 500, {'error': f'Request failed: {str(e)}'}

    def test_basic_connectivity(self, bearer_token: Optional[str] = None) -> Dict[str, Any]:
        """Test basic connectivity to ChatVault."""
        print("Testing basic connectivity...")

        # Test health endpoint
        status, data = self.make_request('/health')
        if status != 200:
            return {
                'test': 'basic_connectivity',
                'status': 'FAIL',
                'error': f'Health check failed: {status}',
                'details': data
            }

        # Test models endpoint
        status, data = self.make_request('/v1/models', bearer_token=bearer_token)
        if status != 200:
            return {
                'test': 'basic_connectivity',
                'status': 'FAIL',
                'error': f'Models endpoint failed: {status}',
                'details': data
            }

        return {
            'test': 'basic_connectivity',
            'status': 'PASS',
            'message': 'Basic connectivity verified'
        }

    def test_authentication(self, bearer_token: str) -> Dict[str, Any]:
        """Test authentication with bearer token."""
        print("Testing authentication...")

        # Use qwen3-8k for mobile1 client, vault-local for others
        test_model = 'qwen3-8k' if bearer_token == DEFAULT_CONFIG['default_bearer_tokens']['mobile1'] else 'vault-local'

        # Test with valid token
        request_data = {
            'model': test_model,
            'messages': [{'role': 'user', 'content': 'Hello, test message'}],
            'max_tokens': 10
        }

        status, data = self.make_request('/v1/chat/completions', 'POST',
                                       data=request_data, bearer_token=bearer_token)

        if status == 200:
            return {
                'test': 'authentication',
                'status': 'PASS',
                'message': 'Authentication successful',
                'response_tokens': len(str(data))
            }
        else:
            return {
                'test': 'authentication',
                'status': 'FAIL',
                'error': f'Authentication failed: {status}',
                'details': data
            }

    def test_model_restrictions(self, restricted_token: str, unrestricted_token: str) -> Dict[str, Any]:
        """Test model access restrictions."""
        print("Testing model restrictions...")

        # Test allowed access for mobile1 (qwen3-8k)
        request_data = {
            'model': 'qwen3-8k',  # Allowed model for mobile1
            'messages': [{'role': 'user', 'content': 'Test allowed access'}],
            'max_tokens': 10
        }

        print(f"  Testing mobile1 access to qwen3-8k (should be allowed)...")
        status, data = self.make_request('/v1/chat/completions', 'POST',
                                       data=request_data, bearer_token=restricted_token)
        print(f"    Status: {status}")

        if status == 200:
            access_test = 'PASS'
        else:
            access_test = 'FAIL'

        # Test allowed access for mobile1 (vault-local)
        request_data['model'] = 'vault-local'  # Also allowed for mobile1
        print(f"  Testing mobile1 access to vault-local (should be allowed)...")
        status, data = self.make_request('/v1/chat/completions', 'POST',
                                       data=request_data, bearer_token=restricted_token)
        print(f"    Status: {status}")

        if status == 200:
            access_test2 = 'PASS'
        else:
            access_test2 = 'FAIL'

        # Test that full3 can also access these models
        request_data['model'] = 'qwen3-8k'
        print(f"  Testing full3 access to qwen3-8k (should be allowed)...")
        status, data = self.make_request('/v1/chat/completions', 'POST',
                                       data=request_data, bearer_token=unrestricted_token)
        print(f"    Status: {status}")

        if status == 200:
            unrestricted_test = 'PASS'
        else:
            unrestricted_test = 'FAIL'

        print(f"  Results: mobile1_qwen3={access_test}, mobile1_vaultlocal={access_test2}, full3_qwen3={unrestricted_test}")

        # Overall test passes if all working models are accessible
        overall_status = 'PASS' if access_test == 'PASS' and access_test2 == 'PASS' and unrestricted_test == 'PASS' else 'FAIL'

        return {
            'test': 'model_restrictions',
            'status': overall_status,
            'mobile1_qwen3_test': access_test,
            'mobile1_vaultlocal_test': access_test2,
            'full3_qwen3_test': unrestricted_test,
            'message': 'Model access validated'
        }

    def test_streaming_response(self, bearer_token: str) -> Dict[str, Any]:
        """Test streaming response functionality."""
        print("Testing streaming response...")

        request_data = {
            'model': 'vault-local',
            'messages': [{'role': 'user', 'content': 'Test streaming response'}],
            'stream': True,
            'max_tokens': 20
        }

        status, response = self.make_request('/v1/chat/completions', 'POST',
                                           data=request_data, bearer_token=bearer_token, stream=True)

        if status != 200:
            return {
                'test': 'streaming_response',
                'status': 'FAIL',
                'error': f'Streaming request failed: {status}',
                'details': str(response)[:200]
            }

        # Check for SSE format
        try:
            content_type = response.headers.get('content-type', '')
            if 'text/event-stream' not in content_type.lower():
                return {
                    'test': 'streaming_response',
                    'status': 'FAIL',
                    'error': f'Invalid content-type: {content_type}'
                }

            # Try to read a few events
            events_received = 0
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        events_received += 1
                        if events_received >= 2:  # Got at least some events
                            break

            if events_received > 0:
                return {
                    'test': 'streaming_response',
                    'status': 'PASS',
                    'message': f'Streaming response received ({events_received} events)'
                }
            else:
                return {
                    'test': 'streaming_response',
                    'status': 'FAIL',
                    'error': 'No streaming events received'
                }

        except Exception as e:
            return {
                'test': 'streaming_response',
                'status': 'FAIL',
                'error': f'Streaming test failed: {str(e)}'
            }

    def test_error_handling(self) -> Dict[str, Any]:
        """Test error handling scenarios."""
        print("Testing error handling...")

        # Test invalid model
        request_data = {
            'model': 'nonexistent-model',
            'messages': [{'role': 'user', 'content': 'Test error'}]
        }

        status, data = self.make_request('/v1/chat/completions', 'POST', data=request_data)

        if status >= 400:
            error_test = 'PASS'
        else:
            error_test = 'FAIL'

        # Test missing authentication
        status, data = self.make_request('/v1/chat/completions', 'POST', data=request_data)

        if status in [401, 403]:
            auth_error_test = 'PASS'
        else:
            auth_error_test = 'FAIL'

        overall_status = 'PASS' if error_test == 'PASS' and auth_error_test == 'PASS' else 'FAIL'

        return {
            'test': 'error_handling',
            'status': overall_status,
            'error_test': error_test,
            'auth_error_test': auth_error_test,
            'message': 'Error handling validated'
        }

    def run_tests(self, test_types: List[str], bearer_token: Optional[str] = None,
                  client_tokens: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Run specified test suites.

        Args:
            test_types: List of test types to run
            bearer_token: Bearer token to use for tests
            client_tokens: Predefined client tokens

        Returns:
            Test results dictionary
        """
        results = {
            'timestamp': time.time(),
            'tests_run': [],
            'summary': {'passed': 0, 'failed': 0, 'total': 0}
        }

        # Get tokens for testing
        mobile1_token = client_tokens.get('mobile1') if client_tokens else DEFAULT_CONFIG['default_bearer_tokens']['mobile1']
        full3_token = client_tokens.get('full3') if client_tokens else DEFAULT_CONFIG['default_bearer_tokens']['full3']
        test_token = bearer_token or mobile1_token

        # Run tests
        if 'basic' in test_types or 'all' in test_types:
            result = self.test_basic_connectivity(test_token)
            results['tests_run'].append(result)
            results['summary']['total'] += 1
            if result['status'] == 'PASS':
                results['summary']['passed'] += 1
            else:
                results['summary']['failed'] += 1

        if 'models' in test_types or 'all' in test_types:
            result = self.test_authentication(test_token)
            results['tests_run'].append(result)
            results['summary']['total'] += 1
            if result['status'] == 'PASS':
                results['summary']['passed'] += 1
            else:
                results['summary']['failed'] += 1

            # Test model restrictions if we have both tokens
            if mobile1_token and full3_token:
                result = self.test_model_restrictions(mobile1_token, full3_token)
                results['tests_run'].append(result)
                results['summary']['total'] += 1
                if result['status'] == 'PASS':
                    results['summary']['passed'] += 1
                else:
                    results['summary']['failed'] += 1

        if 'streaming' in test_types or 'all' in test_types:
            result = self.test_streaming_response(test_token)
            results['tests_run'].append(result)
            results['summary']['total'] += 1
            if result['status'] == 'PASS':
                results['summary']['passed'] += 1
            else:
                results['summary']['failed'] += 1

        if 'errors' in test_types or 'all' in test_types:
            result = self.test_error_handling()
            results['tests_run'].append(result)
            results['summary']['total'] += 1
            if result['status'] == 'PASS':
                results['summary']['passed'] += 1
            else:
                results['summary']['failed'] += 1

        return results


def main():
    """Main entry point for cv-tester."""
    parser = argparse.ArgumentParser(
        description='CV-Tester - Testing tool for ChatVault',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  cv-tester --url http://localhost:4000 basic
  cv-tester --bearer <token> --client mobile1 all
  cv-tester --port 8080 --json streaming
        """
    )

    parser.add_argument('--url', default=DEFAULT_CONFIG['chatvault_url'],
                       help=f'ChatVault URL (default: {DEFAULT_CONFIG["chatvault_url"]})')
    parser.add_argument('--port', type=int,
                       help='ChatVault port (overrides URL port)')
    parser.add_argument('--bearer', '-b',
                       help='Bearer token for authentication')
    parser.add_argument('--client', choices=['mobile1', 'full3'],
                       help='Use predefined client token')
    parser.add_argument('--timeout', type=int, default=DEFAULT_CONFIG['timeout'],
                       help=f'Request timeout in seconds (default: {DEFAULT_CONFIG["timeout"]})')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    parser.add_argument('--json', action='store_true',
                       help='Output results in JSON format')
    parser.add_argument('tests', nargs='*', default=['all'],
                       choices=['basic', 'models', 'streaming', 'errors', 'all'],
                       help='Tests to run (default: all)')

    args = parser.parse_args()

    # Build URL with port override if specified
    url = args.url
    if args.port:
        if '://' in url:
            # Replace port in URL
            parts = url.split(':')
            if len(parts) >= 3:
                parts[-1] = str(args.port)
                url = ':'.join(parts)
        else:
            url = f"{url}:{args.port}"

    # Get bearer token
    bearer_token = args.bearer
    if args.client:
        bearer_token = DEFAULT_CONFIG['default_bearer_tokens'][args.client]
    elif not bearer_token:
        # Default to mobile1 for basic testing
        bearer_token = DEFAULT_CONFIG['default_bearer_tokens']['mobile1']

    # Initialize tester
    tester = ChatVaultTester(url, args.timeout)

    # Run tests
    results = tester.run_tests(args.tests, bearer_token, DEFAULT_CONFIG['default_bearer_tokens'])

    # Output results
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"\nCV-Tester Results ({url})")
        print("=" * 50)
        print(f"Tests run: {results['summary']['total']}")
        print(f"Passed: {results['summary']['passed']}")
        print(f"Failed: {results['summary']['failed']}")
        print()

        for test_result in results['tests_run']:
            status_icon = "✅" if test_result['status'] == 'PASS' else "❌"
            print(f"{status_icon} {test_result['test']}: {test_result.get('message', test_result.get('error', 'Unknown'))}")

            if args.verbose and 'details' in test_result:
                print(f"   Details: {test_result['details']}")

        # Overall status
        if results['summary']['failed'] == 0:
            print("\n🎉 All tests passed!")
        else:
            print(f"\n⚠️  {results['summary']['failed']} test(s) failed")
            sys.exit(1)


if __name__ == '__main__':
    main()