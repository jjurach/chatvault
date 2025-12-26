"""
Authentication and authorization for ChatVault.

This module provides authentication middleware and utilities for securing
the ChatVault API endpoints with Bearer token authentication.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from .config import settings

logger = logging.getLogger(__name__)

# Security scheme for OpenAPI documentation
security = HTTPBearer(auto_error=False)


class Authenticator:
    """
    Handles authentication logic for ChatVault API.

    Supports Bearer token authentication with configurable validation.
    """

    def __init__(self):
        self.api_key = settings.chatvault_api_key
        self.auth_required = settings.auth_required

        # JWT configuration
        self.jwt_secret = settings.jwt_secret
        self.jwt_algorithm = settings.jwt_algorithm
        self.jwt_expiration_hours = settings.jwt_expiration_hours
        self.jwt_refresh_expiration_days = settings.jwt_refresh_expiration_days
        self.jwt_issuer = settings.jwt_issuer

        # Load client configurations for token validation
        self.client_configs = self._load_client_configs()

        # JWT refresh token storage (in production, use Redis/database)
        self.refresh_tokens: Dict[str, Dict[str, Any]] = {}

    def _load_client_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        Load client configurations from the config file.

        Returns:
            Dict mapping client names to their configurations
        """
        try:
            config = settings.get_litellm_config()
            clients = config.get('clients', {})
            logger.debug(f"Loaded {len(clients)} client configurations")
            return clients
        except Exception as e:
            logger.warning(f"Failed to load client configurations: {e}")
            return {}

    def authenticate_token(self, credentials: Optional[HTTPAuthorizationCredentials]) -> Optional[str]:
        """
        Authenticate a Bearer token.

        Args:
            credentials: HTTP Bearer token credentials

        Returns:
            User identifier if authentication successful, None otherwise

        Raises:
            HTTPException: If authentication fails and auth is required
        """
        if not self.auth_required:
            logger.debug("Authentication disabled, allowing request")
            return "anonymous"

        if not credentials:
            if self.auth_required:
                logger.warning("No authentication credentials provided")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return "anonymous"

        if credentials.scheme.lower() != "bearer":
            logger.warning(f"Invalid authentication scheme: {credentials.scheme}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = credentials.credentials

        if not self._validate_token(token):
            logger.warning("Invalid authentication token provided")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # For now, return a generic user ID
        # In the future, this could decode JWT tokens or look up user info
        user_id = self._extract_user_from_token(token)
        logger.debug(f"Authentication successful for user: {user_id}")
        return user_id

    def _validate_token(self, token: str) -> bool:
        """
        Validate an authentication token.

        Supports master API key and client bearer token validation.

        Args:
            token: The token to validate

        Returns:
            True if token is valid, False otherwise
        """
        # Check master API key
        if token == self.api_key:
            return True

        # Check client bearer tokens
        for client_name, client_config in self.client_configs.items():
            expected_token = client_config.get('bearer_token')
            if expected_token and self._constant_time_compare(token, expected_token):
                return True

        # Future: Add JWT validation
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            # Check expiration
            exp = payload.get('exp')
            if exp and datetime.utcnow().timestamp() > exp:
                return False
            return True
        except jwt.PyJWTError:
            pass

        return False

    def _constant_time_compare(self, a: str, b: str) -> bool:
        """
        Constant-time string comparison to prevent timing attacks.

        Args:
            a: First string to compare
            b: Second string to compare

        Returns:
            True if strings are equal, False otherwise
        """
        if len(a) != len(b):
            return False

        # Use XOR to compare bytes
        result = 0
        for x, y in zip(a.encode('utf-8'), b.encode('utf-8')):
            result |= x ^ y

        return result == 0

    def _extract_user_from_token(self, token: str) -> str:
        """
        Extract user identifier from token.

        Args:
            token: Authentication token

        Returns:
            User identifier string
        """
        # Check master API key
        if token == self.api_key:
            return "api_user"

        # Check client tokens and return client name
        for client_name, client_config in self.client_configs.items():
            expected_token = client_config.get('bearer_token')
            if expected_token and self._constant_time_compare(token, expected_token):
                return f"client_{client_name}"

        # Future: Extract from JWT
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            return payload.get('sub', 'jwt_user')
        except jwt.PyJWTError:
            return "unknown_user"

    def validate_model_access(self, user_id: str, model_name: str) -> bool:
        """
        Validate that a user/client has access to a specific model.

        Args:
            user_id: User identifier (from token extraction)
            model_name: Name of the model being requested

        Returns:
            True if access is allowed, False otherwise
        """
        # Master API key has access to all models
        if user_id == "api_user":
            return True

        # Check if this is a client user
        if user_id.startswith("client_"):
            client_name = user_id[7:]  # Remove "client_" prefix
            client_config = self.client_configs.get(client_name)
            if client_config:
                allowed_models = client_config.get('allowed_models', [])
                # Check if client has access to all models
                if '*' in allowed_models:
                    return True
                # Check if requested model is in allowed list
                return model_name in allowed_models

        # Default deny
        return False

    def create_jwt_token(self, user_id: str, expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT access token for a user.

        Args:
            user_id: User identifier
            expires_delta: Token expiration time

        Returns:
            JWT access token string
        """
        if expires_delta is None:
            expires_delta = timedelta(hours=self.jwt_expiration_hours)

        expire = datetime.utcnow() + expires_delta

        to_encode = {
            "sub": user_id,
            "exp": expire.timestamp(),
            "iat": datetime.utcnow().timestamp(),
            "iss": self.jwt_issuer,
            "type": "access"
        }

        encoded_jwt = jwt.encode(to_encode, self.jwt_secret, algorithm=self.jwt_algorithm)
        return encoded_jwt

    def create_refresh_token(self, user_id: str) -> str:
        """
        Create a JWT refresh token for a user.

        Args:
            user_id: User identifier

        Returns:
            JWT refresh token string
        """
        expires_delta = timedelta(days=self.jwt_refresh_expiration_days)
        expire = datetime.utcnow() + expires_delta

        to_encode = {
            "sub": user_id,
            "exp": expire.timestamp(),
            "iat": datetime.utcnow().timestamp(),
            "iss": self.jwt_issuer,
            "type": "refresh",
            "jti": self._generate_token_id()  # Unique token ID for revocation
        }

        refresh_token = jwt.encode(to_encode, self.jwt_secret, algorithm=self.jwt_algorithm)

        # Store refresh token for validation (in production, use Redis/database)
        self.refresh_tokens[refresh_token] = {
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "expires_at": expire
        }

        return refresh_token

    def _generate_token_id(self) -> str:
        """Generate a unique token ID."""
        import uuid
        return str(uuid.uuid4())

    def validate_refresh_token(self, refresh_token: str) -> Optional[str]:
        """
        Validate a refresh token.

        Args:
            refresh_token: The refresh token to validate

        Returns:
            User ID if valid, None otherwise
        """
        try:
            # Check if token exists in our storage
            if refresh_token not in self.refresh_tokens:
                return None

            token_data = self.refresh_tokens[refresh_token]
            if datetime.utcnow() > token_data["expires_at"]:
                # Token expired, remove it
                del self.refresh_tokens[refresh_token]
                return None

            # Decode and validate JWT
            payload = jwt.decode(refresh_token, self.jwt_secret, algorithms=[self.jwt_algorithm])

            # Verify token type
            if payload.get("type") != "refresh":
                return None

            return payload.get("sub")

        except jwt.PyJWTError:
            return None

    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        """
        Create new access token using refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            Dict with new access_token and refresh_token, or None if invalid
        """
        user_id = self.validate_refresh_token(refresh_token)
        if not user_id:
            return None

        # Create new tokens
        new_access_token = self.create_jwt_token(user_id)
        new_refresh_token = self.create_refresh_token(user_id)

        # Remove old refresh token
        if refresh_token in self.refresh_tokens:
            del self.refresh_tokens[refresh_token]

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }

    def authenticate_jwt_user(self, username: str, password: str) -> Optional[Dict[str, str]]:
        """
        Authenticate user with username/password and return JWT tokens.

        Args:
            username: Username
            password: Password

        Returns:
            Dict with tokens if authentication successful, None otherwise
        """
        # For now, this is a placeholder - in production you'd validate against a user database
        # For demo purposes, accept any non-empty username/password
        if not username or not password:
            return None

        # TODO: Implement proper user authentication against database
        # For now, create tokens for any valid credentials
        user_id = f"user_{username}"

        access_token = self.create_jwt_token(user_id)
        refresh_token = self.create_refresh_token(user_id)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": self.jwt_expiration_hours * 3600  # seconds
        }

    def revoke_refresh_token(self, refresh_token: str) -> bool:
        """
        Revoke a refresh token.

        Args:
            refresh_token: Token to revoke

        Returns:
            True if successfully revoked, False otherwise
        """
        if refresh_token in self.refresh_tokens:
            del self.refresh_tokens[refresh_token]
            return True
        return False

    def get_token_from_request(self, request: Request) -> Optional[str]:
        """
        Extract token from request headers.

        Args:
            request: FastAPI request object

        Returns:
            Token string or None
        """
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None

        try:
            scheme, token = auth_header.split(" ", 1)
            if scheme.lower() == "bearer":
                return token
        except ValueError:
            pass

        return None


# Global authenticator instance
authenticator = Authenticator()


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """
    FastAPI dependency for user authentication.

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        User identifier string

    Raises:
        HTTPException: If authentication fails
    """
    return authenticator.authenticate_token(credentials)


def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """
    Synchronous version of authentication dependency.

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        User identifier string

    Raises:
        HTTPException: If authentication fails
    """
    return authenticator.authenticate_token(credentials)


class AuthMiddleware:
    """
    Middleware for handling authentication on all requests.

    Can be used to add authentication to routes that don't use dependencies.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # For now, just pass through
        # Could add global auth checking here if needed
        await self.app(scope, receive, send)


# Utility functions for auth management
def validate_api_key_format(api_key: str) -> bool:
    """
    Validate API key format.

    Args:
        api_key: API key to validate

    Returns:
        True if format is valid
    """
    # Basic validation - should be reasonably long and not empty
    return bool(api_key and len(api_key) >= 16)


def mask_api_key(api_key: str) -> str:
    """
    Mask an API key for logging purposes.

    Args:
        api_key: API key to mask

    Returns:
        Masked version of the key
    """
    if not api_key:
        return ""

    if len(api_key) <= 8:
        return "*" * len(api_key)

    # Show first 4 and last 4 characters
    return f"{api_key[:4]}****{api_key[-4:]}"


def generate_secure_api_key(length: int = 32) -> str:
    """
    Generate a secure random API key.

    Args:
        length: Length of the key

    Returns:
        Random API key string
    """
    import secrets
    import string

    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


# Health check for authentication system
def check_auth_health() -> Dict[str, Any]:
    """
    Check the health of the authentication system.

    Returns:
        Dict with health check results
    """
    health = {
        "auth_enabled": settings.auth_required,
        "api_key_configured": bool(settings.chatvault_api_key),
        "api_key_valid": False,
        "jwt_enabled": False,  # Future feature
    }

    if settings.chatvault_api_key:
        health["api_key_valid"] = validate_api_key_format(settings.chatvault_api_key)

    return health


if __name__ == "__main__":
    # Test authentication functions
    logging.basicConfig(level=logging.INFO)

    print("Auth System Health Check:")
    health = check_auth_health()
    for key, value in health.items():
        print(f"  {key}: {value}")

    print("\nGenerating sample API key:")
    sample_key = generate_secure_api_key()
    print(f"  Key: {sample_key}")
    print(f"  Masked: {mask_api_key(sample_key)}")