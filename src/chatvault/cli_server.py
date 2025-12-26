"""
CLI Server Utilities - Helper functions for server connectivity and management

Provides utilities for checking server health, waiting for startup, and managing
server connections from the CLI.
"""

import time
import requests
from typing import Optional, Tuple
from urllib.parse import urljoin


def check_server_health(base_url: str, timeout: int = 5) -> Tuple[bool, Optional[str]]:
    """
    Check if ChatVault server is running and healthy.

    Args:
        base_url: Base URL of the ChatVault server
        timeout: Request timeout in seconds

    Returns:
        Tuple of (is_healthy, error_message)
    """
    try:
        health_url = urljoin(base_url + '/', 'health')
        response = requests.get(health_url, timeout=timeout)

        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'healthy':
                return True, None
            else:
                return False, f"Server unhealthy: {data.get('status', 'unknown')}"
        else:
            return False, f"Health check failed with status {response.status_code}"

    except requests.exceptions.ConnectionError:
        return False, "Server not running or unreachable"
    except requests.exceptions.Timeout:
        return False, f"Server health check timed out after {timeout} seconds"
    except Exception as e:
        return False, f"Health check error: {str(e)}"


def wait_for_server(base_url: str, timeout: int = 30, check_interval: float = 1.0) -> bool:
    """
    Wait for ChatVault server to become available.

    Args:
        base_url: Base URL of the ChatVault server
        timeout: Maximum time to wait in seconds
        check_interval: Time between health checks

    Returns:
        True if server becomes available, False if timeout
    """
    start_time = time.time()

    print(f"Waiting for ChatVault server at {base_url}...")

    while time.time() - start_time < timeout:
        is_healthy, error = check_server_health(base_url, timeout=5)

        if is_healthy:
            print(f"✅ Server is ready at {base_url}")
            return True

        remaining = int(timeout - (time.time() - start_time))
        print(f"   Server not ready ({error}). Waiting... ({remaining}s remaining)")

        time.sleep(check_interval)

    print(f"❌ Timeout: Server did not become available within {timeout} seconds")
    return False


def make_chat_request(base_url: str, request_data: dict, bearer_token: str,
                     timeout: int = 60) -> Tuple[Optional[dict], Optional[str]]:
    """
    Make a chat completion request to the ChatVault server.

    Args:
        base_url: Base URL of the ChatVault server
        request_data: OpenAI-compatible chat completion request data
        bearer_token: Bearer token for authentication
        timeout: Request timeout in seconds

    Returns:
        Tuple of (response_data, error_message)
    """
    try:
        chat_url = urljoin(base_url + '/', 'v1/chat/completions')
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {bearer_token}'
        }

        response = requests.post(chat_url, headers=headers, json=request_data, timeout=timeout)

        if response.status_code == 200:
            return response.json(), None
        else:
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', f'HTTP {response.status_code}')
            except:
                error_msg = f'HTTP {response.status_code}: {response.text[:200]}'

            return None, error_msg

    except requests.exceptions.ConnectionError:
        return None, "Server not running or unreachable"
    except requests.exceptions.Timeout:
        return None, f"Request timed out after {timeout} seconds"
    except Exception as e:
        return None, f"Request error: {str(e)}"


def get_server_url(host: str = 'localhost', port: int = 4000, protocol: str = 'http') -> str:
    """
    Construct server URL from components.

    Args:
        host: Server hostname
        port: Server port
        protocol: Protocol (http or https)

    Returns:
        Complete server URL
    """
    return f"{protocol}://{host}:{port}"


def validate_server_connection(base_url: str, timeout: int = 10) -> Tuple[bool, str]:
    """
    Validate server connection and return detailed status.

    Args:
        base_url: Base URL of the ChatVault server
        timeout: Connection timeout

    Returns:
        Tuple of (is_valid, status_message)
    """
    # Check basic connectivity
    try:
        response = requests.get(base_url, timeout=timeout)
        if response.status_code >= 200 and response.status_code < 400:
            return True, f"Server responding at {base_url}"
        else:
            return False, f"Server error: HTTP {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, f"Cannot connect to {base_url}"
    except requests.exceptions.Timeout:
        return False, f"Connection timeout to {base_url}"
    except Exception as e:
        return False, f"Connection error: {str(e)}"