"""
Data models for ChatVault SDK

Pydantic models for API requests and responses.
"""

from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime


class Message(BaseModel):
    """Chat message model"""

    role: str = Field(..., description="Role of the message sender")
    content: Union[str, List[Dict[str, Any]]] = Field(..., description="Content of the message")
    name: Optional[str] = Field(None, description="Optional name for the message sender")


class ChatCompletionRequest(BaseModel):
    """Request model for chat completions"""

    model: str = Field(..., description="Model to use for completion")
    messages: List[Message] = Field(..., description="List of messages")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, gt=0, description="Maximum tokens to generate")
    stream: Optional[bool] = Field(False, description="Enable streaming response")
    stop: Optional[Union[str, List[str]]] = Field(None, description="Stop sequences")
    presence_penalty: Optional[float] = Field(0.0, ge=-2.0, le=2.0, description="Presence penalty")
    frequency_penalty: Optional[float] = Field(0.0, ge=-2.0, le=2.0, description="Frequency penalty")
    logit_bias: Optional[Dict[str, float]] = Field(None, description="Logit bias adjustments")
    user: Optional[str] = Field(None, description="Unique user identifier")


class ChatCompletionChoice(BaseModel):
    """Choice model for chat completion responses"""

    index: int = Field(..., description="Choice index")
    message: Message = Field(..., description="The message content")
    finish_reason: Optional[str] = Field(None, description="Reason completion finished")


class ChatCompletionUsage(BaseModel):
    """Usage statistics for chat completions"""

    prompt_tokens: int = Field(..., description="Number of tokens in the prompt")
    completion_tokens: int = Field(..., description="Number of tokens in the completion")
    total_tokens: int = Field(..., description="Total number of tokens used")


class ChatCompletion(BaseModel):
    """Response model for chat completions"""

    id: str = Field(..., description="Unique identifier for the completion")
    object: str = Field("chat.completion", description="Object type")
    created: int = Field(..., description="Unix timestamp of creation")
    model: str = Field(..., description="Model used for completion")
    choices: List[ChatCompletionChoice] = Field(..., description="List of completion choices")
    usage: ChatCompletionUsage = Field(..., description="Token usage statistics")


class ModelInfo(BaseModel):
    """Model information"""

    id: str = Field(..., description="Model identifier")
    object: str = Field("model", description="Object type")
    created: int = Field(..., description="Unix timestamp of creation")
    owned_by: str = Field(..., description="Organization that owns the model")


class ModelList(BaseModel):
    """List of available models"""

    object: str = Field("list", description="Object type")
    data: List[ModelInfo] = Field(..., description="List of model objects")


class UsageLog(BaseModel):
    """Individual usage log entry"""

    timestamp: datetime = Field(..., description="When the request was made")
    model_name: str = Field(..., description="Model used")
    input_tokens: int = Field(..., description="Input token count")
    output_tokens: int = Field(..., description="Output token count")
    total_tokens: int = Field(..., description="Total token count")
    cost: float = Field(..., description="Cost in USD")
    provider: Optional[str] = Field(None, description="LLM provider")
    response_time_ms: int = Field(..., description="Response time in milliseconds")
    status_code: int = Field(..., description="HTTP status code")
    request_id: str = Field(..., description="Unique request identifier")


class UsageStats(BaseModel):
    """Usage statistics response"""

    user_id: str = Field(..., description="User identifier")
    pagination: Dict[str, Any] = Field(..., description="Pagination information")
    filters: Dict[str, Any] = Field(..., description="Applied filters")
    aggregations: Dict[str, Any] = Field(..., description="Aggregated statistics")
    usage_logs: List[UsageLog] = Field(..., description="Individual usage logs")


class ModelRecommendation(BaseModel):
    """Model recommendation with score"""

    model: str = Field(..., description="Recommended model name")
    score: float = Field(..., description="Recommendation score")
    rank: int = Field(..., description="Recommendation rank")


class ModelRecommendations(BaseModel):
    """Model recommendations response"""

    recommendations: List[ModelRecommendation] = Field(..., description="List of recommendations")
    total_available: int = Field(..., description="Total available models")
    limit: int = Field(..., description="Requested limit")


class HealthStatus(BaseModel):
    """Health check response"""

    status: str = Field(..., description="Overall health status")
    timestamp: float = Field(..., description="Health check timestamp")
    version: str = Field(..., description="API version")
    components: Dict[str, Dict[str, Any]] = Field(..., description="Component health details")


class JWTTokens(BaseModel):
    """JWT authentication tokens"""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration time in seconds")


class BudgetStatus(BaseModel):
    """Budget status response"""

    budget_status: Dict[str, Any] = Field(..., description="Budget status details")
    model_breakdown: List[Dict[str, Any]] = Field(..., description="Cost breakdown by model")
    currency: str = Field(..., description="Currency code")