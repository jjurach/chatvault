"""
ChatVault SDK - Python client for ChatVault API

Example usage:
    from chatvault import ChatVault

    client = ChatVault(api_key="your-api-key", base_url="https://your-chatvault.com")

    # Simple chat completion
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello!"}]
    )

    # Get usage statistics
    usage = client.usage.list(limit=10)

    # Get model recommendations
    recommendations = client.models.recommend(
        messages=[{"role": "user", "content": "Write Python code"}]
    )
"""

from .client import ChatVault
from .models import Message, ChatCompletion, UsageStats
from .exceptions import ChatVaultError, AuthenticationError, RateLimitError

__version__ = "1.0.0"
__all__ = [
    "ChatVault",
    "Message",
    "ChatCompletion",
    "UsageStats",
    "ChatVaultError",
    "AuthenticationError",
    "RateLimitError",
]