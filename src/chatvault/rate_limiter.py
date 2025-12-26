"""
Rate limiting functionality for ChatVault.

This module provides sliding window rate limiting with configurable limits per user/client.
Uses in-memory storage for rate limiting counters (in production, use Redis).
"""

import time
import logging
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from .config import settings

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_minute: int = 100
    window_seconds: int = 60  # Sliding window size


@dataclass
class RateLimitEntry:
    """Entry for tracking requests within a sliding window."""
    timestamp: float
    count: int = 1


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter using in-memory storage.

    Tracks requests per user/client within a configurable time window.
    Uses a deque to maintain request timestamps for efficient sliding window calculation.
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        # user_id -> deque of (timestamp, request_count) tuples
        self.user_windows: Dict[str, deque] = defaultdict(deque)
        self.cleanup_interval = 300  # Clean up old entries every 5 minutes
        self.last_cleanup = time.time()

    def is_allowed(self, user_id: str) -> Tuple[bool, Dict[str, any]]:
        """
        Check if a request from the given user is allowed.

        Args:
            user_id: User identifier

        Returns:
            Tuple of (allowed: bool, info: dict with rate limit details)
        """
        current_time = time.time()
        window_start = current_time - self.config.window_seconds

        # Clean up old entries periodically
        if current_time - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_entries(current_time)
            self.last_cleanup = current_time

        user_window = self.user_windows[user_id]

        # Remove entries outside the sliding window
        while user_window and user_window[0].timestamp < window_start:
            user_window.popleft()

        # Count requests in current window
        total_requests = sum(entry.count for entry in user_window)

        # Check if limit exceeded
        allowed = total_requests < self.config.requests_per_minute

        if allowed:
            # Add current request to window
            if user_window and user_window[-1].timestamp == current_time:
                # If same timestamp, increment count
                user_window[-1].count += 1
            else:
                # Add new entry
                user_window.append(RateLimitEntry(timestamp=current_time))

        # Calculate reset time (when oldest request expires)
        reset_time = None
        if user_window:
            reset_time = user_window[0].timestamp + self.config.window_seconds

        info = {
            "limit": self.config.requests_per_minute,
            "remaining": max(0, self.config.requests_per_minute - total_requests - (0 if allowed else 1)),
            "reset": int(reset_time) if reset_time else int(current_time + self.config.window_seconds),
            "window_seconds": self.config.window_seconds
        }

        return allowed, info

    def _cleanup_old_entries(self, current_time: float):
        """Clean up old entries across all users."""
        window_start = current_time - self.config.window_seconds

        for user_id in list(self.user_windows.keys()):
            user_window = self.user_windows[user_id]

            # Remove old entries
            while user_window and user_window[0].timestamp < window_start:
                user_window.popleft()

            # Remove empty user entries
            if not user_window:
                del self.user_windows[user_id]

        logger.debug(f"Cleaned up rate limiting data, {len(self.user_windows)} active users")

    def get_user_stats(self, user_id: str) -> Dict[str, any]:
        """Get rate limiting statistics for a specific user."""
        current_time = time.time()
        window_start = current_time - self.config.window_seconds

        user_window = self.user_windows.get(user_id, deque())

        # Clean old entries for this user
        while user_window and user_window[0].timestamp < window_start:
            user_window.popleft()

        total_requests = sum(entry.count for entry in user_window)

        return {
            "user_id": user_id,
            "current_requests": total_requests,
            "limit": self.config.requests_per_minute,
            "window_seconds": self.config.window_seconds,
            "entries_in_window": len(user_window)
        }

    def reset_user(self, user_id: str):
        """Reset rate limiting for a specific user."""
        if user_id in self.user_windows:
            del self.user_windows[user_id]
            logger.info(f"Reset rate limiting for user: {user_id}")


# Global rate limiter instance
rate_limiter = SlidingWindowRateLimiter()


def get_user_rate_limit_config(user_id: str) -> RateLimitConfig:
    """
    Get rate limit configuration for a specific user.

    Args:
        user_id: User identifier

    Returns:
        RateLimitConfig for the user
    """
    # Get base configuration from settings
    config = settings.get_litellm_config()
    router_settings = config.get('router_settings', {})
    rate_limit_settings = router_settings.get('rate_limit_per_user', {})

    requests_per_minute = rate_limit_settings.get('requests_per_minute', settings.rate_limit_requests)

    # Check if this is a client user with custom limits
    if user_id.startswith("client_"):
        client_name = user_id[7:]  # Remove "client_" prefix
        clients = config.get('clients', {})
        client_config = clients.get(client_name, {})
        # Could add client-specific rate limits here in the future

    return RateLimitConfig(
        requests_per_minute=requests_per_minute,
        window_seconds=60  # 1 minute window
    )


def check_rate_limit(user_id: str) -> Tuple[bool, Dict[str, any]]:
    """
    Check if a user is within their rate limit.

    Args:
        user_id: User identifier

    Returns:
        Tuple of (allowed: bool, info: dict with rate limit details)
    """
    # Get user-specific configuration
    config = get_user_rate_limit_config(user_id)

    # Update global rate limiter config if different
    if rate_limiter.config.requests_per_minute != config.requests_per_minute:
        rate_limiter.config = config

    return rate_limiter.is_allowed(user_id)


def get_rate_limit_stats(user_id: str) -> Dict[str, any]:
    """
    Get rate limiting statistics for a user.

    Args:
        user_id: User identifier

    Returns:
        Dict with rate limiting statistics
    """
    return rate_limiter.get_user_stats(user_id)


# Rate limiting middleware for FastAPI
class RateLimitMiddleware:
    """
    FastAPI middleware for rate limiting.

    Checks rate limits before processing requests and adds appropriate headers to responses.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract user ID from request (this would need to be enhanced for production)
        # For now, we'll get it from a header or use anonymous
        # In production, this should extract from JWT or session

        # For demo purposes, check a custom header
        headers = dict((k.decode(), v.decode()) for k, v in scope.get("headers", []))
        user_id = headers.get("x-user-id", "anonymous")

        # Check rate limit
        allowed, limit_info = check_rate_limit(user_id)

        if not allowed:
            # Rate limit exceeded
            logger.warning(f"Rate limit exceeded for user: {user_id}")

            # Create rate limit exceeded response
            response_headers = [
                (b"content-type", b"application/json"),
                (b"x-ratelimit-limit", str(limit_info["limit"]).encode()),
                (b"x-ratelimit-remaining", str(limit_info["remaining"]).encode()),
                (b"x-ratelimit-reset", str(limit_info["reset"]).encode()),
                (b"x-ratelimit-window", str(limit_info["window_seconds"]).encode()),
            ]

            response_body = {
                "error": {
                    "message": "Rate limit exceeded",
                    "type": "rate_limit_error",
                    "code": 429
                }
            }

            import json
            response_data = json.dumps(response_body).encode()

            await send({
                "type": "http.response.start",
                "status": 429,
                "headers": response_headers,
            })
            await send({
                "type": "http.response.body",
                "body": response_data,
            })
            return

        # Rate limit passed, add headers to response
        original_send = send

        async def modified_send(message):
            if message["type"] == "http.response.start":
                # Add rate limit headers to successful responses
                headers = list(message.get("headers", []))
                headers.extend([
                    (b"x-ratelimit-limit", str(limit_info["limit"]).encode()),
                    (b"x-ratelimit-remaining", str(limit_info["remaining"]).encode()),
                    (b"x-ratelimit-reset", str(limit_info["reset"]).encode()),
                    (b"x-ratelimit-window", str(limit_info["window_seconds"]).encode()),
                ])
                message["headers"] = headers

            await original_send(message)

        await self.app(scope, receive, modified_send)


# Utility functions for rate limit management
def reset_user_rate_limit(user_id: str):
    """Reset rate limiting for a specific user."""
    rate_limiter.reset_user(user_id)


def get_all_rate_limit_stats() -> Dict[str, Dict[str, any]]:
    """Get rate limiting statistics for all users."""
    return {user_id: rate_limiter.get_user_stats(user_id) for user_id in rate_limiter.user_windows.keys()}


if __name__ == "__main__":
    # Test rate limiting functionality
    logging.basicConfig(level=logging.INFO)

    limiter = SlidingWindowRateLimiter()

    # Test basic functionality
    user_id = "test_user"

    print("Testing rate limiter...")

    # Should allow first 100 requests
    for i in range(105):
        allowed, info = limiter.is_allowed(user_id)
        if i < 100:
            assert allowed, f"Request {i+1} should be allowed"
        else:
            assert not allowed, f"Request {i+1} should be blocked"

        if i == 50:
            print(f"After 50 requests: {info}")

    print(f"After 105 requests: {info}")
    print("Rate limiting test passed!")