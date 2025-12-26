"""
Load balancing and provider management for ChatVault.

This module provides advanced load balancing capabilities across multiple LLM provider
instances, including health monitoring, failover, and performance-based routing.
"""

import asyncio
import logging
import time
import random
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque

from .config import settings
from .metrics import record_external_api_call

logger = logging.getLogger(__name__)


class LoadBalancingAlgorithm(Enum):
    """Supported load balancing algorithms."""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    RANDOM = "random"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"


class ProviderStatus(Enum):
    """Provider instance health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    MAINTENANCE = "maintenance"


@dataclass
class ProviderInstance:
    """
    Represents a single provider instance with health and performance tracking.
    """
    provider_name: str
    instance_id: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    weight: int = 1  # For weighted algorithms
    max_concurrent_requests: int = 10
    timeout: int = 30

    # Health and performance tracking
    status: ProviderStatus = ProviderStatus.HEALTHY
    last_health_check: float = field(default_factory=time.time)
    health_check_interval: int = 60  # seconds
    consecutive_failures: int = 0
    max_consecutive_failures: int = 3

    # Circuit breaker
    circuit_breaker_open: bool = False
    circuit_breaker_timeout: int = 300  # 5 minutes
    last_circuit_failure: Optional[float] = None

    # Performance metrics
    active_requests: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    last_response_time: Optional[float] = None

    # Request queue for rate limiting
    request_queue: deque = field(default_factory=deque)
    max_queue_size: int = 100

    def __post_init__(self):
        """Initialize after dataclass creation."""
        if not self.instance_id:
            self.instance_id = f"{self.provider_name}_{id(self)}"

    def is_healthy(self) -> bool:
        """Check if the provider instance is healthy."""
        if self.circuit_breaker_open:
            # Check if circuit breaker should be reset
            if (self.last_circuit_failure and
                time.time() - self.last_circuit_failure > self.circuit_breaker_timeout):
                self.circuit_breaker_open = False
                self.consecutive_failures = 0
                logger.info(f"Circuit breaker reset for {self.instance_id}")
            else:
                return False

        return self.status in [ProviderStatus.HEALTHY, ProviderStatus.DEGRADED]

    def can_accept_request(self) -> bool:
        """Check if this instance can accept a new request."""
        if not self.is_healthy():
            return False

        if self.active_requests >= self.max_concurrent_requests:
            return False

        if len(self.request_queue) >= self.max_queue_size:
            return False

        return True

    def record_request_start(self):
        """Record the start of a request."""
        self.active_requests += 1
        self.total_requests += 1

    def record_request_complete(self, success: bool, response_time: Optional[float] = None):
        """Record the completion of a request."""
        self.active_requests = max(0, self.active_requests - 1)

        if success:
            self.successful_requests += 1
            self.consecutive_failures = 0
            if response_time is not None:
                self.update_response_time(response_time)
        else:
            self.failed_requests += 1
            self.consecutive_failures += 1

            # Check for circuit breaker activation
            if self.consecutive_failures >= self.max_consecutive_failures:
                self.circuit_breaker_open = True
                self.last_circuit_failure = time.time()
                logger.warning(f"Circuit breaker activated for {self.instance_id}")

    def update_response_time(self, response_time: float):
        """Update average response time using exponential moving average."""
        if self.last_response_time is None:
            self.avg_response_time = response_time
        else:
            # Exponential moving average with alpha=0.1
            alpha = 0.1
            self.avg_response_time = alpha * response_time + (1 - alpha) * self.avg_response_time

        self.last_response_time = response_time

    def get_load_factor(self) -> float:
        """Get the current load factor (0.0 to 1.0)."""
        if self.max_concurrent_requests == 0:
            return 1.0
        return min(1.0, self.active_requests / self.max_concurrent_requests)

    def to_dict(self) -> Dict[str, Any]:
        """Convert instance to dictionary for monitoring."""
        return {
            "provider_name": self.provider_name,
            "instance_id": self.instance_id,
            "status": self.status.value,
            "healthy": self.is_healthy(),
            "active_requests": self.active_requests,
            "total_requests": self.total_requests,
            "success_rate": (self.successful_requests / max(1, self.total_requests)) * 100,
            "avg_response_time": round(self.avg_response_time, 3),
            "load_factor": round(self.get_load_factor(), 3),
            "circuit_breaker_open": self.circuit_breaker_open,
            "queue_size": len(self.request_queue),
            "last_health_check": self.last_health_check
        }


@dataclass
class ProviderPool:
    """
    Pool of provider instances for a specific model/provider combination.
    """
    model_name: str
    provider_name: str
    instances: List[ProviderInstance] = field(default_factory=list)
    algorithm: LoadBalancingAlgorithm = LoadBalancingAlgorithm.ROUND_ROBIN

    # Round-robin state
    round_robin_index: int = 0

    def add_instance(self, instance: ProviderInstance):
        """Add a provider instance to the pool."""
        self.instances.append(instance)
        logger.info(f"Added instance {instance.instance_id} to pool {self.model_name}")

    def remove_instance(self, instance_id: str):
        """Remove a provider instance from the pool."""
        self.instances = [inst for inst in self.instances if inst.instance_id != instance_id]
        logger.info(f"Removed instance {instance_id} from pool {self.model_name}")

    def get_healthy_instances(self) -> List[ProviderInstance]:
        """Get all healthy instances."""
        return [inst for inst in self.instances if inst.is_healthy()]

    def select_instance(self) -> Optional[ProviderInstance]:
        """
        Select a provider instance using the configured load balancing algorithm.
        """
        healthy_instances = self.get_healthy_instances()
        if not healthy_instances:
            logger.warning(f"No healthy instances available for {self.model_name}")
            return None

        if self.algorithm == LoadBalancingAlgorithm.ROUND_ROBIN:
            return self._select_round_robin(healthy_instances)
        elif self.algorithm == LoadBalancingAlgorithm.LEAST_LOADED:
            return self._select_least_loaded(healthy_instances)
        elif self.algorithm == LoadBalancingAlgorithm.RANDOM:
            return self._select_random(healthy_instances)
        elif self.algorithm == LoadBalancingAlgorithm.WEIGHTED_ROUND_ROBIN:
            return self._select_weighted_round_robin(healthy_instances)
        else:
            # Default to round-robin
            return self._select_round_robin(healthy_instances)

    def _select_round_robin(self, instances: List[ProviderInstance]) -> ProviderInstance:
        """Select instance using round-robin algorithm."""
        instance = instances[self.round_robin_index % len(instances)]
        self.round_robin_index = (self.round_robin_index + 1) % len(instances)
        return instance

    def _select_least_loaded(self, instances: List[ProviderInstance]) -> ProviderInstance:
        """Select instance with lowest load factor."""
        return min(instances, key=lambda inst: inst.get_load_factor())

    def _select_random(self, instances: List[ProviderInstance]) -> ProviderInstance:
        """Select instance randomly."""
        return random.choice(instances)

    def _select_weighted_round_robin(self, instances: List[ProviderInstance]) -> ProviderInstance:
        """Select instance using weighted round-robin."""
        # Simple implementation - can be enhanced
        total_weight = sum(inst.weight for inst in instances)
        if total_weight == 0:
            return self._select_round_robin(instances)

        # This is a simplified version - a full implementation would track current position
        weights = [inst.weight for inst in instances]
        choice = random.choices(instances, weights=weights, k=1)[0]
        return choice

    def get_pool_stats(self) -> Dict[str, Any]:
        """Get statistics for the entire pool."""
        healthy_instances = self.get_healthy_instances()
        total_instances = len(self.instances)

        return {
            "model_name": self.model_name,
            "provider_name": self.provider_name,
            "algorithm": self.algorithm.value,
            "total_instances": total_instances,
            "healthy_instances": len(healthy_instances),
            "health_percentage": (len(healthy_instances) / max(1, total_instances)) * 100,
            "instances": [inst.to_dict() for inst in self.instances]
        }


class LoadBalancer:
    """
    Main load balancer managing multiple provider pools and routing decisions.
    """

    def __init__(self):
        self.pools: Dict[str, ProviderPool] = {}
        self.health_check_task: Optional[asyncio.Task] = None
        self.health_check_interval = 60  # seconds

        # Load configuration
        self._load_configuration()

        # Start health checking
        if settings.debug:
            # Only start in debug mode to avoid issues in tests
            pass
        else:
            self.start_health_checks()

    def _load_configuration(self):
        """Load load balancing configuration."""
        config = settings.get_litellm_config()
        router_settings = config.get('router_settings', {})

        # Default algorithm
        default_algorithm = LoadBalancingAlgorithm.ROUND_ROBIN
        algorithm_str = router_settings.get('load_balancing', {}).get('algorithm', 'round_robin')
        try:
            default_algorithm = LoadBalancingAlgorithm(algorithm_str)
        except ValueError:
            logger.warning(f"Invalid load balancing algorithm: {algorithm_str}, using round_robin")

        # Create pools for each model
        for model_config in config.get('model_list', []):
            model_name = model_config.get('model_name')
            if not model_name:
                continue

            provider_name = self._determine_provider(model_config)
            pool = ProviderPool(
                model_name=model_name,
                provider_name=provider_name,
                algorithm=default_algorithm
            )

            # Create provider instances
            instances_config = router_settings.get('load_balancing', {}).get('instances', {}).get(model_name, [])

            if not instances_config:
                # Create single default instance
                instance = ProviderInstance(
                    provider_name=provider_name,
                    instance_id=f"{provider_name}_default",
                    weight=1
                )
                pool.add_instance(instance)
            else:
                # Create configured instances
                for i, inst_config in enumerate(instances_config):
                    instance = ProviderInstance(
                        provider_name=provider_name,
                        instance_id=inst_config.get('id', f"{provider_name}_{i}"),
                        base_url=inst_config.get('base_url'),
                        api_key=inst_config.get('api_key'),
                        weight=inst_config.get('weight', 1),
                        max_concurrent_requests=inst_config.get('max_concurrent', 10),
                        timeout=inst_config.get('timeout', 30)
                    )
                    pool.add_instance(instance)

            self.pools[model_name] = pool
            logger.info(f"Created load balancing pool for {model_name} with {len(pool.instances)} instances")

    def _determine_provider(self, model_config: Dict[str, Any]) -> str:
        """Determine provider name from model configuration."""
        litellm_params = model_config.get('litellm_params', {})
        model = litellm_params.get('model', '')

        if model.startswith('claude'):
            return 'anthropic'
        elif model.startswith('deepseek'):
            return 'deepseek'
        elif model.startswith('gpt') or model.startswith('text-'):
            return 'openai'
        elif ':' in model:  # Ollama models
            return 'ollama'
        elif model.startswith('gemini'):
            return 'google'
        else:
            return 'unknown'

    def select_instance(self, model_name: str) -> Optional[ProviderInstance]:
        """
        Select a provider instance for the given model using load balancing.
        """
        pool = self.pools.get(model_name)
        if not pool:
            logger.warning(f"No load balancing pool found for model: {model_name}")
            return None

        return pool.select_instance()

    def record_request(self, model_name: str, instance_id: str, success: bool, response_time: Optional[float] = None):
        """Record the result of a request for load balancing decisions."""
        pool = self.pools.get(model_name)
        if pool:
            for instance in pool.instances:
                if instance.instance_id == instance_id:
                    instance.record_request_complete(success, response_time)
                    break

    def get_pool_stats(self, model_name: Optional[str] = None) -> Dict[str, Any]:
        """Get load balancing statistics."""
        if model_name:
            pool = self.pools.get(model_name)
            if pool:
                return pool.get_pool_stats()
            else:
                return {"error": f"No pool found for model: {model_name}"}

        # Return stats for all pools
        return {
            "pools": {name: pool.get_pool_stats() for name, pool in self.pools.items()},
            "total_pools": len(self.pools),
            "healthy_pools": sum(1 for pool in self.pools.values() if pool.get_healthy_instances())
        }

    async def _health_check_loop(self):
        """Background task for periodic health checks."""
        while True:
            try:
                await self._perform_health_checks()
            except Exception as e:
                logger.error(f"Health check error: {e}")

            await asyncio.sleep(self.health_check_interval)

    async def _perform_health_checks(self):
        """Perform health checks on all provider instances."""
        logger.debug("Performing health checks on all provider instances")

        for pool in self.pools.values():
            for instance in pool.instances:
                await self._check_instance_health(instance)

    async def _check_instance_health(self, instance: ProviderInstance):
        """Check health of a single provider instance."""
        current_time = time.time()
        if current_time - instance.last_health_check < instance.health_check_interval:
            return  # Skip if not time for health check yet

        instance.last_health_check = current_time

        try:
            # Perform health check based on provider type
            if instance.provider_name == 'ollama':
                healthy = await self._check_ollama_health(instance)
            elif instance.provider_name in ['openai', 'anthropic', 'deepseek']:
                healthy = await self._check_api_provider_health(instance)
            else:
                # Default health check
                healthy = True

            # Update instance status
            if healthy:
                if instance.status != ProviderStatus.HEALTHY:
                    logger.info(f"Instance {instance.instance_id} is now healthy")
                instance.status = ProviderStatus.HEALTHY
            else:
                if instance.status == ProviderStatus.HEALTHY:
                    logger.warning(f"Instance {instance.instance_id} is now unhealthy")
                instance.status = ProviderStatus.UNHEALTHY

        except Exception as e:
            logger.error(f"Health check failed for {instance.instance_id}: {e}")
            instance.status = ProviderStatus.UNHEALTHY

    async def _check_ollama_health(self, instance: ProviderInstance) -> bool:
        """Check Ollama instance health."""
        try:
            import httpx
            base_url = instance.base_url or "http://localhost:11434"

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    async def _check_api_provider_health(self, instance: ProviderInstance) -> bool:
        """Check API provider health (simplified check)."""
        # For API providers, we could make a lightweight API call
        # For now, just check if we have required configuration
        if instance.provider_name == 'openai' and not instance.api_key:
            return False
        if instance.provider_name == 'anthropic' and not instance.api_key:
            return False
        if instance.provider_name == 'deepseek' and not instance.api_key:
            return False

        # Consider the instance healthy if configured properly
        return True

    def start_health_checks(self):
        """Start the background health check task."""
        if self.health_check_task and not self.health_check_task.done():
            return  # Already running

        self.health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("Started load balancer health checks")

    def stop_health_checks(self):
        """Stop the background health check task."""
        if self.health_check_task and not self.health_check_task.done():
            self.health_check_task.cancel()
            logger.info("Stopped load balancer health checks")


# Global load balancer instance
load_balancer = LoadBalancer()


# Convenience functions
def get_instance_for_model(model_name: str) -> Optional[ProviderInstance]:
    """Get a load-balanced instance for the given model."""
    return load_balancer.select_instance(model_name)


def record_request_result(model_name: str, instance_id: str, success: bool, response_time: Optional[float] = None):
    """Record the result of a request."""
    load_balancer.record_request(model_name, instance_id, success, response_time)


def get_load_balancer_stats(model_name: Optional[str] = None) -> Dict[str, Any]:
    """Get load balancer statistics."""
    return load_balancer.get_pool_stats(model_name)


if __name__ == "__main__":
    # Test load balancing functionality
    logging.basicConfig(level=logging.INFO)

    # Create a test pool
    pool = ProviderPool("test-model", "test-provider")

    # Add some instances
    for i in range(3):
        instance = ProviderInstance(
            provider_name="test-provider",
            instance_id=f"instance_{i}",
            weight=i + 1  # Different weights
        )
        pool.add_instance(instance)

    print("Testing Load Balancing...")

    # Test different algorithms
    algorithms = [
        LoadBalancingAlgorithm.ROUND_ROBIN,
        LoadBalancingAlgorithm.LEAST_LOADED,
        LoadBalancingAlgorithm.RANDOM,
        LoadBalancingAlgorithm.WEIGHTED_ROUND_ROBIN
    ]

    for algorithm in algorithms:
        pool.algorithm = algorithm
        print(f"\nTesting {algorithm.value}:")

        selections = []
        for _ in range(10):
            instance = pool.select_instance()
            if instance:
                selections.append(instance.instance_id)

        print(f"Selections: {selections}")

    print("\nLoad balancing test completed!")