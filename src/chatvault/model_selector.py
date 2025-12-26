"""
Dynamic model selection and intelligent routing for ChatVault.

This module provides context-aware model selection based on request characteristics,
performance profiling, A/B testing capabilities, and intelligent model recommendations.
"""

import logging
import time
import random
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import json

from .config import settings

logger = logging.getLogger(__name__)


class ModelCapability(Enum):
    """Model capabilities and specializations."""
    GENERAL_CHAT = "general_chat"
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    MATHEMATICAL = "mathematical"
    CREATIVE_WRITING = "creative_writing"
    ANALYSIS = "analysis"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"
    QUESTION_ANSWERING = "question_answering"
    CONVERSATIONAL = "conversational"


class ContextType(Enum):
    """Types of request context for intelligent routing."""
    TECHNICAL = "technical"
    CREATIVE = "creative"
    ANALYTICAL = "analytical"
    EDUCATIONAL = "educational"
    BUSINESS = "business"
    CASUAL = "casual"
    CODE = "code"
    MATH = "math"
    UNKNOWN = "unknown"


@dataclass
class ModelProfile:
    """
    Performance profile for a model based on usage data.
    """
    model_name: str
    provider: str

    # Performance metrics
    avg_response_time: float = 0.0
    success_rate: float = 1.0
    avg_cost_per_token: float = 0.0
    total_requests: int = 0
    total_tokens: int = 0

    # Quality metrics
    user_rating: Optional[float] = None
    error_rate: float = 0.0

    # Capabilities and strengths
    capabilities: List[ModelCapability] = field(default_factory=list)
    context_types: List[ContextType] = field(default_factory=list)

    # A/B testing
    experiment_groups: List[str] = field(default_factory=list)

    def update_performance(self, response_time: float, success: bool, tokens: int, cost: float):
        """Update performance metrics with new request data."""
        # Exponential moving average for response time
        if self.avg_response_time == 0:
            self.avg_response_time = response_time
        else:
            alpha = 0.1  # Smoothing factor
            self.avg_response_time = alpha * response_time + (1 - alpha) * self.avg_response_time

        # Update success rate
        self.total_requests += 1
        if success:
            success_count = int(self.success_rate * (self.total_requests - 1)) + 1
        else:
            success_count = int(self.success_rate * (self.total_requests - 1))
        self.success_rate = success_count / self.total_requests

        # Update cost metrics
        self.total_tokens += tokens
        if self.total_tokens > 0:
            total_cost = self.avg_cost_per_token * (self.total_tokens - tokens) + cost
            self.avg_cost_per_token = total_cost / self.total_tokens

        # Update error rate
        if not success:
            self.error_rate = ((self.error_rate * (self.total_requests - 1)) + 1) / self.total_requests
        else:
            self.error_rate = (self.error_rate * (self.total_requests - 1)) / self.total_requests

    def get_score(self, context: 'RequestContext') -> float:
        """Calculate a suitability score for this model given the request context."""
        score = 100.0  # Base score

        # Capability matching
        capability_match = len(set(self.capabilities) & set(context.detected_capabilities))
        if capability_match > 0:
            score += capability_match * 20  # Bonus for capability matches
        elif self.capabilities and context.detected_capabilities:
            score -= 30  # Penalty for no capability matches

        # Context type matching
        context_match = 1 if context.context_type in self.context_types else 0
        score += context_match * 15

        # Performance factors
        if self.avg_response_time > 0:
            # Prefer faster models (inverse relationship)
            speed_score = max(0, 10 - (self.avg_response_time / 1000))  # Assume <10s is good
            score += speed_score

        # Success rate bonus
        score += (self.success_rate - 0.5) * 20  # Bonus/penalty around 50% success

        # Cost efficiency (prefer lower cost for same capability)
        if self.avg_cost_per_token > 0:
            cost_score = max(0, 5 - (self.avg_cost_per_token * 100000))  # Prefer cheaper models
            score += cost_score

        return max(0, score)  # Ensure non-negative score


@dataclass
class RequestContext:
    """
    Context information extracted from a chat request for intelligent routing.
    """
    messages: List[Dict[str, Any]]
    model: Optional[str] = None
    user_id: Optional[str] = None

    # Detected characteristics
    context_type: ContextType = ContextType.UNKNOWN
    detected_capabilities: List[ModelCapability] = field(default_factory=list)
    complexity_score: float = 0.0  # 0-1 scale
    length_score: float = 0.0  # 0-1 scale
    technical_terms: List[str] = field(default_factory=list)
    language_code: str = "en"

    # Request metadata
    timestamp: float = field(default_factory=time.time)
    request_id: Optional[str] = None


class Experiment:
    """
    A/B testing experiment for model comparison.
    """
    def __init__(self, experiment_id: str, name: str, models: List[str],
                 traffic_percentage: float = 10.0, start_time: Optional[float] = None):
        self.experiment_id = experiment_id
        self.name = name
        self.models = models
        self.traffic_percentage = traffic_percentage
        self.start_time = start_time or time.time()
        self.end_time: Optional[float] = None

        # Results tracking
        self.model_results: Dict[str, Dict[str, Any]] = {
            model: {"requests": 0, "successes": 0, "avg_response_time": 0.0, "user_feedback": []}
            for model in models
        }

    def is_active(self) -> bool:
        """Check if experiment is currently active."""
        return self.end_time is None

    def should_include_request(self, user_id: str) -> bool:
        """Determine if a request should be included in this experiment."""
        if not self.is_active():
            return False

        # Use user_id for consistent routing to experiment groups
        hash_value = hash(f"{self.experiment_id}_{user_id}") % 100
        return hash_value < self.traffic_percentage

    def get_test_model(self, user_id: str) -> Optional[str]:
        """Get the test model for a user (deterministic based on user_id)."""
        if not self.should_include_request(user_id):
            return None

        # Deterministic model selection based on user_id
        model_index = hash(f"{self.experiment_id}_{user_id}_model") % len(self.models)
        return self.models[model_index]

    def record_result(self, model: str, success: bool, response_time: float, user_feedback: Optional[int] = None):
        """Record experiment results."""
        if model not in self.model_results:
            return

        results = self.model_results[model]
        results["requests"] += 1

        if success:
            results["successes"] += 1

        # Update average response time
        current_avg = results["avg_response_time"]
        current_count = results["requests"]
        results["avg_response_time"] = ((current_avg * (current_count - 1)) + response_time) / current_count

        if user_feedback is not None:
            results["user_feedback"].append(user_feedback)

    def get_results(self) -> Dict[str, Any]:
        """Get experiment results."""
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "models": self.models,
            "traffic_percentage": self.traffic_percentage,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "is_active": self.is_active(),
            "results": self.model_results
        }


class DynamicModelSelector:
    """
    Intelligent model selection engine with context awareness and A/B testing.
    """

    def __init__(self):
        self.model_profiles: Dict[str, ModelProfile] = {}
        self.experiments: Dict[str, Experiment] = {}
        self.context_analyzer = ContextAnalyzer()

        # Load configuration
        self._load_configuration()

        logger.info(f"Dynamic model selector initialized with {len(self.model_profiles)} model profiles")

    def _load_configuration(self):
        """Load model profiles and experiment configuration."""
        config = settings.get_litellm_config()

        # Load model capabilities from configuration
        model_routing = config.get('model_routing', {})
        capabilities_config = model_routing.get('capabilities', {})
        experiments_config = model_routing.get('experiments', {})

        # Create model profiles for all available models
        available_models = settings.get_available_models()
        for model_name in available_models:
            provider = settings.get_provider_for_model(model_name)

            # Get capabilities from config or infer from model name
            model_caps = capabilities_config.get(model_name, [])
            capabilities = [ModelCapability(cap) for cap in model_caps if cap in ModelCapability.__members__]

            if not capabilities:
                # Infer capabilities from model name
                capabilities = self._infer_capabilities_from_name(model_name)

            # Create profile
            profile = ModelProfile(
                model_name=model_name,
                provider=provider or "unknown",
                capabilities=capabilities,
                context_types=self._infer_context_types(capabilities)
            )

            self.model_profiles[model_name] = profile

        # Load experiments
        for exp_config in experiments_config:
            experiment = Experiment(
                experiment_id=exp_config['id'],
                name=exp_config['name'],
                models=exp_config['models'],
                traffic_percentage=exp_config.get('traffic_percentage', 10.0)
            )
            self.experiments[exp_config['id']] = experiment

    def _infer_capabilities_from_name(self, model_name: str) -> List[ModelCapability]:
        """Infer model capabilities from model name."""
        name_lower = model_name.lower()
        capabilities = [ModelCapability.GENERAL_CHAT]  # Default

        # Code-related models
        if any(term in name_lower for term in ['code', 'coder', 'program', 'dev']):
            capabilities.append(ModelCapability.CODE_GENERATION)
            capabilities.append(ModelCapability.CODE_REVIEW)

        # Math-related models
        if any(term in name_lower for term in ['math', 'calculate', 'numerical']):
            capabilities.append(ModelCapability.MATHEMATICAL)

        # Creative models
        if any(term in name_lower for term in ['creative', 'write', 'story', 'art']):
            capabilities.append(ModelCapability.CREATIVE_WRITING)

        # Analysis models
        if any(term in name_lower for term in ['analyze', 'research', 'study']):
            capabilities.append(ModelCapability.ANALYSIS)

        return capabilities

    def _infer_context_types(self, capabilities: List[ModelCapability]) -> List[ContextType]:
        """Infer context types from capabilities."""
        context_types = []

        capability_to_context = {
            ModelCapability.CODE_GENERATION: ContextType.CODE,
            ModelCapability.CODE_REVIEW: ContextType.CODE,
            ModelCapability.MATHEMATICAL: ContextType.MATH,
            ModelCapability.ANALYSIS: ContextType.ANALYTICAL,
            ModelCapability.CREATIVE_WRITING: ContextType.CREATIVE,
            ModelCapability.QUESTION_ANSWERING: ContextType.EDUCATIONAL,
            ModelCapability.BUSINESS: ContextType.BUSINESS,
            ModelCapability.CONVERSATIONAL: ContextType.CASUAL
        }

        for capability in capabilities:
            if capability in capability_to_context:
                context_type = capability_to_context[capability]
                if context_type not in context_types:
                    context_types.append(context_type)

        return context_types

    def select_model(self, request_context: RequestContext, user_id: Optional[str] = None) -> str:
        """
        Select the best model for a request based on context and performance.

        Args:
            request_context: Analyzed request context
            user_id: User identifier for A/B testing

        Returns:
            Selected model name
        """
        # Check for active experiments first
        if user_id:
            experiment_model = self._check_experiments(user_id, request_context)
            if experiment_model:
                return experiment_model

        # Get available models
        available_models = list(self.model_profiles.keys())

        if request_context.model and request_context.model in available_models:
            # Specific model requested
            return request_context.model

        # Score all available models
        model_scores = {}
        for model_name in available_models:
            profile = self.model_profiles[model_name]
            score = profile.get_score(request_context)
            model_scores[model_name] = score

        # Select highest scoring model
        best_model = max(model_scores.items(), key=lambda x: x[1])[0]

        logger.info(f"Selected model {best_model} for request (score: {model_scores[best_model]:.1f})")
        return best_model

    def _check_experiments(self, user_id: str, request_context: RequestContext) -> Optional[str]:
        """Check if user should be included in any active experiments."""
        for experiment in self.experiments.values():
            if experiment.is_active():
                test_model = experiment.get_test_model(user_id)
                if test_model and test_model in self.model_profiles:
                    logger.info(f"User {user_id} selected for experiment {experiment.experiment_id}: {test_model}")
                    return test_model

        return None

    def analyze_request_context(self, messages: List[Dict[str, Any]],
                              requested_model: Optional[str] = None,
                              user_id: Optional[str] = None) -> RequestContext:
        """Analyze request content to determine context and requirements."""
        return self.context_analyzer.analyze(messages, requested_model, user_id)

    def update_model_performance(self, model_name: str, response_time: float,
                               success: bool, tokens: int, cost: float):
        """Update performance metrics for a model."""
        if model_name in self.model_profiles:
            self.model_profiles[model_name].update_performance(response_time, success, tokens, cost)

    def record_experiment_result(self, experiment_id: str, model: str,
                               success: bool, response_time: float,
                               user_feedback: Optional[int] = None):
        """Record results for an A/B testing experiment."""
        if experiment_id in self.experiments:
            self.experiments[experiment_id].record_result(model, success, response_time, user_feedback)

    def get_model_recommendations(self, context: RequestContext, limit: int = 3) -> List[Tuple[str, float]]:
        """Get model recommendations with scores for a given context."""
        model_scores = []
        for model_name, profile in self.model_profiles.items():
            score = profile.get_score(context)
            model_scores.append((model_name, score))

        # Sort by score descending and return top N
        model_scores.sort(key=lambda x: x[1], reverse=True)
        return model_scores[:limit]

    def get_model_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Get all model profiles for monitoring."""
        return {
            model_name: {
                "provider": profile.provider,
                "capabilities": [cap.value for cap in profile.capabilities],
                "context_types": [ctx.value for ctx in profile.context_types],
                "performance": {
                    "avg_response_time": profile.avg_response_time,
                    "success_rate": profile.success_rate,
                    "avg_cost_per_token": profile.avg_cost_per_token,
                    "total_requests": profile.total_requests,
                    "error_rate": profile.error_rate
                }
            }
            for model_name, profile in self.model_profiles.items()
        }

    def get_experiment_results(self) -> Dict[str, Any]:
        """Get results for all experiments."""
        return {
            exp_id: experiment.get_results()
            for exp_id, experiment in self.experiments.items()
        }


class ContextAnalyzer:
    """
    Analyzes request content to determine context type and required capabilities.
    """

    def __init__(self):
        # Keywords for different contexts and capabilities
        self.context_keywords = {
            ContextType.TECHNICAL: [
                'code', 'programming', 'function', 'class', 'variable', 'algorithm',
                'debug', 'error', 'exception', 'api', 'database', 'server', 'framework'
            ],
            ContextType.CODE: [
                'def ', 'import ', 'class ', 'function', 'variable', 'syntax', 'compile',
                'runtime', 'library', 'package', 'module', 'git', 'repository'
            ],
            ContextType.MATH: [
                'calculate', 'equation', 'formula', 'mathematical', 'algebra', 'geometry',
                'calculus', 'statistics', 'probability', 'theorem', 'proof', 'integral'
            ],
            ContextType.ANALYTICAL: [
                'analyze', 'analysis', 'research', 'study', 'evaluate', 'assess',
                'compare', 'contrast', 'examine', 'investigate', 'data', 'metrics'
            ],
            ContextType.CREATIVE: [
                'creative', 'write', 'story', 'poem', 'novel', 'art', 'design',
                'imagine', 'fiction', 'narrative', 'character', 'plot'
            ],
            ContextType.EDUCATIONAL: [
                'explain', 'teach', 'learn', 'understand', 'concept', 'tutorial',
                'guide', 'lesson', 'course', 'study', 'homework', 'assignment'
            ]
        }

        self.capability_keywords = {
            ModelCapability.CODE_GENERATION: ['write code', 'implement', 'function', 'script', 'program'],
            ModelCapability.CODE_REVIEW: ['review', 'bug', 'fix', 'improve', 'optimize', 'refactor'],
            ModelCapability.MATHEMATICAL: ['solve', 'calculate', 'equation', 'math', 'formula'],
            ModelCapability.ANALYSIS: ['analyze', 'compare', 'evaluate', 'assess', 'research'],
            ModelCapability.SUMMARIZATION: ['summarize', 'summary', 'overview', 'brief', 'condense'],
            ModelCapability.QUESTION_ANSWERING: ['what', 'how', 'why', 'explain', 'describe']
        }

    def analyze(self, messages: List[Dict[str, Any]],
               requested_model: Optional[str] = None,
               user_id: Optional[str] = None) -> RequestContext:
        """Analyze messages to determine context and capabilities."""

        # Extract text content from messages
        text_content = self._extract_text_content(messages)
        text_lower = text_content.lower()

        # Detect context type
        context_type = self._detect_context_type(text_lower)

        # Detect required capabilities
        detected_capabilities = self._detect_capabilities(text_lower)

        # Calculate complexity and length scores
        complexity_score = self._calculate_complexity(text_content)
        length_score = min(1.0, len(text_content) / 2000)  # Normalize to 0-1

        # Extract technical terms
        technical_terms = self._extract_technical_terms(text_lower)

        return RequestContext(
            messages=messages,
            model=requested_model,
            user_id=user_id,
            context_type=context_type,
            detected_capabilities=detected_capabilities,
            complexity_score=complexity_score,
            length_score=length_score,
            technical_terms=technical_terms
        )

    def _extract_text_content(self, messages: List[Dict[str, Any]]) -> str:
        """Extract text content from chat messages."""
        text_parts = []
        for message in messages:
            if isinstance(message.get('content'), str):
                text_parts.append(message['content'])
            elif isinstance(message.get('content'), list):
                # Handle structured content (e.g., with images)
                for part in message['content']:
                    if part.get('type') == 'text':
                        text_parts.append(part.get('text', ''))

        return ' '.join(text_parts)

    def _detect_context_type(self, text: str) -> ContextType:
        """Detect the primary context type from text."""
        context_scores = {}

        for context_type, keywords in self.context_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text)
            context_scores[context_type] = score

        if context_scores:
            best_context = max(context_scores.items(), key=lambda x: x[1])
            if best_context[1] > 0:  # Require at least one match
                return best_context[0]

        return ContextType.UNKNOWN

    def _detect_capabilities(self, text: str) -> List[ModelCapability]:
        """Detect required capabilities from text."""
        capabilities = []

        for capability, keywords in self.capability_keywords.items():
            if any(keyword in text for keyword in keywords):
                capabilities.append(capability)

        # Add general capabilities based on context
        if not capabilities:
            capabilities.append(ModelCapability.GENERAL_CHAT)

        return capabilities

    def _calculate_complexity(self, text: str) -> float:
        """Calculate text complexity score (0-1)."""
        if not text:
            return 0.0

        # Factors: length, vocabulary diversity, technical terms
        length_factor = min(1.0, len(text) / 1000)
        sentence_count = text.count('.') + text.count('!') + text.count('?')
        avg_sentence_length = len(text) / max(1, sentence_count)

        # Technical term density
        technical_terms = self._extract_technical_terms(text.lower())
        technical_density = len(technical_terms) / max(1, len(text.split()))

        complexity = (length_factor * 0.3 + min(1.0, avg_sentence_length / 50) * 0.3 +
                     technical_density * 0.4)

        return min(1.0, complexity)

    def _extract_technical_terms(self, text: str) -> List[str]:
        """Extract technical terms from text."""
        # Simple technical term detection
        technical_indicators = [
            'api', 'http', 'json', 'xml', 'sql', 'database', 'server', 'client',
            'function', 'method', 'class', 'object', 'variable', 'algorithm',
            'debug', 'error', 'exception', 'compile', 'runtime'
        ]

        found_terms = []
        for term in technical_indicators:
            if term in text:
                found_terms.append(term)

        return list(set(found_terms))  # Remove duplicates


# Global instances
model_selector = DynamicModelSelector()


# Convenience functions
def select_model_for_request(messages: List[Dict[str, Any]],
                           requested_model: Optional[str] = None,
                           user_id: Optional[str] = None) -> str:
    """Select the best model for a request."""
    context = model_selector.analyze_request_context(messages, requested_model, user_id)
    return model_selector.select_model(context, user_id)


def update_model_performance(model_name: str, response_time: float,
                           success: bool, tokens: int, cost: float):
    """Update performance data for a model."""
    model_selector.update_model_performance(model_name, response_time, success, tokens, cost)


def get_model_recommendations(messages: List[Dict[str, Any]], limit: int = 3) -> List[Tuple[str, float]]:
    """Get model recommendations for a request."""
    context = model_selector.analyze_request_context(messages)
    return model_selector.get_model_recommendations(context, limit)


def get_model_profiles() -> Dict[str, Any]:
    """Get all model profiles for monitoring."""
    return model_selector.get_model_profiles()


if __name__ == "__main__":
    # Test dynamic model selection
    logging.basicConfig(level=logging.INFO)

    print("Testing Dynamic Model Selection...")

    # Test context analysis
    test_messages = [
        {"role": "user", "content": "Write a Python function to calculate fibonacci numbers"}
    ]

    context = model_selector.analyze_request_context(test_messages)
    print(f"Detected context: {context.context_type.value}")
    print(f"Detected capabilities: {[cap.value for cap in context.detected_capabilities]}")

    # Test model selection
    selected_model = model_selector.select_model(context)
    print(f"Selected model: {selected_model}")

    # Test recommendations
    recommendations = model_selector.get_model_recommendations(context, 3)
    print(f"Top recommendations: {recommendations}")

    print("\nDynamic model selection test completed!")