#!/usr/bin/env python3
"""
ChatVault Demo Script

This script demonstrates the basic functionality of ChatVault by connecting
to local Ollama instance and making test requests to the ChatVault API.
"""

import requests
import json
import time
import argparse
from typing import Optional, Dict, Any


class ChatVaultDemo:
    """
    Demo class for testing ChatVault functionality.
    """

    def __init__(self, base_url: str = "http://localhost:4000", api_key: Optional[str] = None):
        """
        Initialize the demo client.

        Args:
            base_url: Base URL of the ChatVault server
            api_key: API key for authentication (if required)
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()

        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
        })

        if self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}'
            })

    def test_health_check(self) -> Dict[str, Any]:
        """
        Test the health check endpoint.

        Returns:
            Dict containing health status
        """
        print("🔍 Testing health check endpoint...")

        try:
            response = self.session.get(f"{self.base_url}/health")
            response.raise_for_status()
            health = response.json()

            print("✅ Health check successful")
            print(f"   Status: {health.get('status', 'unknown')}")
            print(f"   Version: {health.get('version', 'unknown')}")

            # Check components
            components = health.get('components', {})
            for component, status in components.items():
                comp_status = status.get('status', 'unknown')
                status_icon = "✅" if comp_status == "healthy" else "❌"
                print(f"   {component}: {status_icon} {comp_status}")

            return health

        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return {"error": str(e)}

    def test_models_endpoint(self) -> Dict[str, Any]:
        """
        Test the models listing endpoint.

        Returns:
            Dict containing available models
        """
        print("\n📋 Testing models endpoint...")

        try:
            response = self.session.get(f"{self.base_url}/v1/models")
            response.raise_for_status()
            models_data = response.json()

            print("✅ Models endpoint successful")
            models = models_data.get('data', [])
            print(f"   Available models: {len(models)}")

            for model in models:
                model_id = model.get('id', 'unknown')
                provider = model.get('owned_by', 'unknown')
                print(f"   - {model_id} (provider: {provider})")

            return models_data

        except Exception as e:
            print(f"❌ Models endpoint failed: {e}")
            return {"error": str(e)}

    def test_chat_completion(self, model: str, message: str, stream: bool = False) -> Dict[str, Any]:
        """
        Test the chat completions endpoint.

        Args:
            model: Model name to use
            message: Message to send
            stream: Whether to use streaming response

        Returns:
            Dict containing completion response
        """
        print(f"\n💬 Testing chat completion (model: {model}, stream: {stream})...")

        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": message}
            ],
            "stream": stream,
            "max_tokens": 100  # Limit response length for demo
        }

        try:
            if stream:
                # Handle streaming response
                response = self.session.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=payload,
                    stream=True
                )
                response.raise_for_status()

                print("✅ Streaming response started")
                full_content = ""

                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            data = line[6:]  # Remove 'data: ' prefix

                            if data == '[DONE]':
                                print("\n✅ Streaming completed")
                                break

                            try:
                                chunk = json.loads(data)
                                if chunk.get('object') == 'chat.completion.chunk':
                                    choices = chunk.get('choices', [])
                                    if choices:
                                        delta = choices[0].get('delta', {})
                                        content = delta.get('content', '')
                                        if content:
                                            print(content, end='', flush=True)
                                            full_content += content
                            except json.JSONDecodeError:
                                continue

                return {"content": full_content, "streamed": True}

            else:
                # Handle regular response
                response = self.session.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=payload
                )
                response.raise_for_status()
                result = response.json()

                print("✅ Chat completion successful")
                choices = result.get('choices', [])
                if choices:
                    content = choices[0].get('message', {}).get('content', '')
                    print(f"Response: {content}")

                    # Show usage info
                    usage = result.get('usage', {})
                    if usage:
                        print(f"Usage: {usage.get('total_tokens', 0)} tokens")

                return result

        except Exception as e:
            print(f"❌ Chat completion failed: {e}")
            return {"error": str(e)}

    def run_full_demo(self):
        """
        Run the complete demo suite.
        """
        print("🚀 ChatVault Demo Starting...")
        print(f"   Target: {self.base_url}")
        print(f"   Auth: {'Enabled' if self.api_key else 'Disabled'}")
        print()

        # Test 1: Health Check
        health = self.test_health_check()
        if health.get('status') != 'healthy':
            print("❌ System is not healthy. Aborting demo.")
            return

        # Test 2: Models
        models = self.test_models_endpoint()
        available_models = []
        if 'data' in models:
            available_models = [m.get('id') for m in models['data']]

        if not available_models:
            print("❌ No models available. Aborting demo.")
            return

        # Test 3: Chat Completion (non-streaming)
        test_model = available_models[0]  # Use first available model
        self.test_chat_completion(
            model=test_model,
            message="Hello! This is a test message from ChatVault demo. Please respond briefly.",
            stream=False
        )

        # Test 4: Chat Completion (streaming) - if supported
        print("\n⏳ Waiting 2 seconds before streaming test...")
        time.sleep(2)

        self.test_chat_completion(
            model=test_model,
            message="Tell me a short joke.",
            stream=True
        )

        print("\n🎉 Demo completed successfully!")


def main():
    """
    Main entry point for the demo script.
    """
    parser = argparse.ArgumentParser(description="ChatVault Demo Script")
    parser.add_argument(
        '--url',
        default='http://localhost:4000',
        help='ChatVault server URL (default: http://localhost:4000)'
    )
    parser.add_argument(
        '--api-key',
        help='API key for authentication'
    )
    parser.add_argument(
        '--model',
        help='Specific model to test (optional)'
    )
    parser.add_argument(
        '--message',
        default='Hello, can you help me test ChatVault?',
        help='Test message to send'
    )
    parser.add_argument(
        '--stream',
        action='store_true',
        help='Use streaming response'
    )

    args = parser.parse_args()

    # Create demo client
    demo = ChatVaultDemo(args.url, args.api_key)

    if args.model:
        # Run single test
        demo.test_chat_completion(args.model, args.message, args.stream)
    else:
        # Run full demo suite
        demo.run_full_demo()


if __name__ == "__main__":
    main()