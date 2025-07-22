"""
Error Recovery and Self-Healing System for EzzInv
Automatically detects, diagnoses, and resolves system issues
"""

import asyncio
import json
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
import subprocess
import sys
from pathlib import Path

from ..config.settings import Settings
from ..memory.enhanced_memory import EnhancedMemoryManager, MemoryTier
from ..mcp.installer import MCPServerInstaller
from ..automation.performance_tuning import PerformanceAutoTuner
from ..automation.dynamic_config import DynamicConfigManager
from ..utils.logging import get_logger

logger = get_logger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels"""

    CRITICAL = "critical"  # System-breaking errors
    HIGH = "high"  # Major functionality impacted
    MEDIUM = "medium"  # Some features affected
    LOW = "low"  # Minor issues


class ErrorCategory(str, Enum):
    """Categories of errors"""

    PROVIDER_FAILURE = "provider_failure"
    MEMORY_SYSTEM = "memory_system"
    MCP_SERVER = "mcp_server"
    DATABASE_CONNECTION = "database_connection"
    NETWORK_TIMEOUT = "network_timeout"
    CONFIGURATION = "configuration"
    DEPENDENCY_MISSING = "dependency_missing"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    AUTHENTICATION = "authentication"
    RESOURCE_EXHAUSTION = "resource_exhaustion"


class RecoveryAction(str, Enum):
    """Available recovery actions"""

    RESTART_SERVICE = "restart_service"
    FAILOVER_PROVIDER = "failover_provider"
    CLEAR_CACHE = "clear_cache"
    RESET_CONNECTION = "reset_connection"
    INSTALL_DEPENDENCY = "install_dependency"
    ROLLBACK_CONFIG = "rollback_config"
    SCALE_RESOURCES = "scale_resources"
    SWITCH_MCP_SERVER = "switch_mcp_server"
    EMERGENCY_MODE = "emergency_mode"
    RESTART_COMPONENT = "restart_component"


@dataclass
class ErrorEvent:
    """Represents an error event"""

    id: str
    timestamp: datetime
    error_type: str
    error_message: str
    stack_trace: str
    severity: ErrorSeverity
    category: ErrorCategory
    component: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolution_timestamp: Optional[datetime] = None
    recovery_actions_taken: List[str] = field(default_factory=list)
    recurrence_count: int = 1


@dataclass
class RecoveryRule:
    """Rule for automatic error recovery"""

    name: str
    error_pattern: str  # Regex pattern to match error messages
    category: ErrorCategory
    severity: ErrorSeverity
    actions: List[RecoveryAction]
    conditions: Dict[str, Any] = field(default_factory=dict)  # Additional conditions
    max_attempts: int = 3
    cooldown_minutes: int = 10
    success_rate_threshold: float = 0.7  # Minimum success rate to keep using this rule
    enabled: bool = True
    last_used: Optional[datetime] = None
    success_count: int = 0
    failure_count: int = 0


class ErrorRecoverySystem:
    """
    Error Recovery and Self-Healing System
    Monitors for errors and automatically applies recovery strategies
    """

    def __init__(
        self,
        settings: Settings,
        memory_manager: EnhancedMemoryManager,
        performance_tuner: PerformanceAutoTuner,
        config_manager: DynamicConfigManager,
    ):
        self.settings = settings
        self.memory = memory_manager
        self.performance_tuner = performance_tuner
        self.config_manager = config_manager
        self.mcp_installer = MCPServerInstaller(settings)

        # Error tracking
        self.error_events: Dict[str, ErrorEvent] = {}
        self.error_patterns: Dict[str, int] = {}  # Track frequency of error patterns
        self.recovery_history: List[Dict[str, Any]] = []

        # Recovery configuration
        self.max_concurrent_recoveries = 3
        self.error_detection_interval = 30  # seconds
        self.error_retention_days = 30
        self.emergency_mode_active = False

        # Component health tracking
        self.component_health: Dict[str, Dict[str, Any]] = {}
        self.last_health_check = datetime.now()

        # Initialize recovery rules
        self.recovery_rules = self._create_recovery_rules()

        # Active recovery tasks
        self.active_recoveries: Dict[str, asyncio.Task] = {}

    async def start_error_monitoring(self):
        """Start continuous error monitoring and recovery"""
        logger.info("Starting error recovery system...")

        # Start monitoring loops
        monitor_tasks = [
            asyncio.create_task(self._error_detection_loop()),
            asyncio.create_task(self._health_check_loop()),
            asyncio.create_task(self._recovery_cleanup_loop()),
            asyncio.create_task(self._pattern_analysis_loop()),
        ]

        try:
            await asyncio.gather(*monitor_tasks)
        except Exception as e:
            logger.error(f"Error monitoring system failed: {e}")
            await self._initiate_emergency_recovery()

    async def _error_detection_loop(self):
        """Continuous error detection loop"""
        while True:
            try:
                await self._scan_for_errors()
                await asyncio.sleep(self.error_detection_interval)
            except Exception as e:
                logger.error(f"Error in detection loop: {e}")
                await asyncio.sleep(60)  # Longer wait on error

    async def _health_check_loop(self):
        """Continuous health check loop"""
        while True:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(300)  # Every 5 minutes
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(300)

    async def _recovery_cleanup_loop(self):
        """Clean up completed recoveries and old data"""
        while True:
            try:
                await self._cleanup_completed_recoveries()
                await self._cleanup_old_errors()
                await asyncio.sleep(3600)  # Every hour
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(3600)

    async def _pattern_analysis_loop(self):
        """Analyze error patterns and optimize recovery rules"""
        while True:
            try:
                await self._analyze_error_patterns()
                await self._optimize_recovery_rules()
                await asyncio.sleep(1800)  # Every 30 minutes
            except Exception as e:
                logger.error(f"Error in pattern analysis loop: {e}")
                await asyncio.sleep(1800)

    async def _scan_for_errors(self):
        """Scan system for errors"""
        # Check recent log entries for errors
        await self._check_application_logs()

        # Check component health
        await self._check_component_status()

        # Check performance metrics for anomalies
        await self._check_performance_anomalies()

        # Check external dependencies
        await self._check_external_dependencies()

    async def _check_application_logs(self):
        """Check application logs for recent errors"""
        try:
            # Get recent error logs from memory system
            recent_logs = await self.memory.get_analytics_data(
                minutes=5, metrics=["error", "exception", "failure"]
            )

            for log_entry in recent_logs:
                if log_entry.get("error") or log_entry.get("exception"):
                    await self._process_error_event(
                        error_type=log_entry.get("error_type", "application_error"),
                        error_message=log_entry.get("message", ""),
                        stack_trace=log_entry.get("stack_trace", ""),
                        component=log_entry.get("component", "unknown"),
                        metadata=log_entry,
                    )

        except Exception as e:
            logger.error(f"Error checking application logs: {e}")

    async def _check_component_status(self):
        """Check status of system components"""
        components = {
            "memory_system": self._check_memory_system,
            "chat_completion": self._check_chat_completion,
            "mcp_servers": self._check_mcp_servers,
            "database": self._check_database,
            "cache": self._check_cache_system,
        }

        for component, check_func in components.items():
            try:
                status = await check_func()
                self.component_health[component] = {
                    "status": status,
                    "last_check": datetime.now(),
                    "consecutive_failures": (
                        0
                        if status["healthy"]
                        else self.component_health.get(component, {}).get(
                            "consecutive_failures", 0
                        )
                        + 1
                    ),
                }

                # Trigger recovery if component is unhealthy
                if not status["healthy"]:
                    await self._process_component_failure(component, status)

            except Exception as e:
                logger.error(f"Error checking component {component}: {e}")
                await self._process_error_event(
                    error_type="component_check_failure",
                    error_message=f"Failed to check {component}: {str(e)}",
                    stack_trace=traceback.format_exc(),
                    component=component,
                )

    async def _check_memory_system(self) -> Dict[str, Any]:
        """Check memory system health"""
        try:
            # Test Redis connection
            redis_status = await self.memory._test_redis_connection()

            # Test MongoDB connection
            mongo_status = await self.memory._test_mongodb_connection()

            # Test PostgreSQL connection
            postgres_status = await self.memory._test_postgres_connection()

            # Check cache performance
            cache_stats = await self.memory.get_cache_statistics()

            healthy = all([redis_status, mongo_status, postgres_status])

            return {
                "healthy": healthy,
                "redis": redis_status,
                "mongodb": mongo_status,
                "postgresql": postgres_status,
                "cache_hit_rate": cache_stats.get("hit_rate", 0),
                "total_memory_usage": cache_stats.get("memory_usage", 0),
            }

        except Exception as e:
            return {"healthy": False, "error": str(e)}

    async def _check_chat_completion(self) -> Dict[str, Any]:
        """Check chat completion system health"""
        try:
            # Test each provider
            from ..chat.enhanced_completion import EnhancedChatCompletion

            chat_system = EnhancedChatCompletion(self.settings, self.memory)
            provider_status = await chat_system.test_all_providers()

            healthy_providers = sum(
                1 for status in provider_status.values() if status.get("healthy", False)
            )
            total_providers = len(provider_status)

            return {
                "healthy": healthy_providers > 0,
                "provider_status": provider_status,
                "healthy_providers": healthy_providers,
                "total_providers": total_providers,
                "availability_ratio": (
                    healthy_providers / total_providers if total_providers > 0 else 0
                ),
            }

        except Exception as e:
            return {"healthy": False, "error": str(e)}

    async def _check_mcp_servers(self) -> Dict[str, Any]:
        """Check MCP servers health"""
        try:
            from ..mcp.manager import MCPServerManager

            mcp_manager = MCPServerManager(self.settings)
            server_status = await mcp_manager.get_all_server_status()

            active_servers = sum(
                1 for status in server_status.values() if status.get("active", False)
            )
            total_servers = len(server_status)

            return {
                "healthy": active_servers > 0,
                "server_status": server_status,
                "active_servers": active_servers,
                "total_servers": total_servers,
                "availability_ratio": (
                    active_servers / total_servers if total_servers > 0 else 0
                ),
            }

        except Exception as e:
            return {"healthy": False, "error": str(e)}

    async def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity"""
        try:
            # Test database connection
            from sqlalchemy.ext.asyncio import create_async_engine
            from sqlalchemy import text

            engine = create_async_engine(self.settings.database_url)

            async with engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                await result.fetchone()

            await engine.dispose()

            return {"healthy": True, "connection": "active"}

        except Exception as e:
            return {"healthy": False, "error": str(e)}

    async def _check_cache_system(self) -> Dict[str, Any]:
        """Check cache system health"""
        try:
            cache_stats = await self.memory.get_cache_statistics()

            # Check if cache is responding and performing well
            hit_rate = cache_stats.get("hit_rate", 0)
            response_time = cache_stats.get("avg_response_time", 0)

            healthy = hit_rate > 0.1 and response_time < 100  # 100ms threshold

            return {
                "healthy": healthy,
                "hit_rate": hit_rate,
                "response_time": response_time,
                "memory_usage": cache_stats.get("memory_usage", 0),
            }

        except Exception as e:
            return {"healthy": False, "error": str(e)}

    async def _check_performance_anomalies(self):
        """Check for performance anomalies that might indicate errors"""
        try:
            performance_status = await self.performance_tuner.get_performance_status()
            current_metrics = performance_status.get("current_metrics", {})

            # Check for anomalies
            anomalies = []

            response_time = current_metrics.get("response_time", 0)
            if response_time > 30:  # 30 second threshold
                anomalies.append(
                    {
                        "type": "high_response_time",
                        "value": response_time,
                        "threshold": 30,
                    }
                )

            error_rate = current_metrics.get("error_rate", 0)
            if error_rate > 0.2:  # 20% error rate threshold
                anomalies.append(
                    {"type": "high_error_rate", "value": error_rate, "threshold": 0.2}
                )

            memory_usage = current_metrics.get("memory_usage", 0)
            if memory_usage > 0.9:  # 90% memory usage threshold
                anomalies.append(
                    {
                        "type": "high_memory_usage",
                        "value": memory_usage,
                        "threshold": 0.9,
                    }
                )

            # Process anomalies as potential errors
            for anomaly in anomalies:
                await self._process_error_event(
                    error_type="performance_anomaly",
                    error_message=f"Performance anomaly detected: {anomaly['type']}",
                    stack_trace="",
                    component="performance_monitor",
                    metadata=anomaly,
                )

        except Exception as e:
            logger.error(f"Error checking performance anomalies: {e}")

    async def _check_external_dependencies(self):
        """Check external dependencies"""
        dependencies = [
            ("redis", "redis://localhost:6379"),
            ("mongodb", "mongodb://localhost:27017"),
            ("postgresql", self.settings.database_url),
        ]

        for dep_name, dep_url in dependencies:
            try:
                # Simple connection test
                if dep_name == "redis":
                    import redis.asyncio as redis

                    r = redis.from_url(dep_url)
                    await r.ping()
                    await r.close()

                elif dep_name == "mongodb":
                    from motor.motor_asyncio import AsyncIOMotorClient

                    client = AsyncIOMotorClient(dep_url)
                    await client.admin.command('ping')
                    client.close()

                elif dep_name == "postgresql":
                    from sqlalchemy.ext.asyncio import create_async_engine
                    from sqlalchemy import text

                    engine = create_async_engine(dep_url)
                    async with engine.begin() as conn:
                        await conn.execute(text("SELECT 1"))
                    await engine.dispose()

            except Exception as e:
                await self._process_error_event(
                    error_type="dependency_failure",
                    error_message=f"Dependency {dep_name} is unavailable: {str(e)}",
                    stack_trace=traceback.format_exc(),
                    component="dependency_check",
                    metadata={"dependency": dep_name, "url": dep_url},
                )

    async def _process_error_event(
        self,
        error_type: str,
        error_message: str,
        stack_trace: str,
        component: str,
        metadata: Dict[str, Any] = None,
    ):
        """Process a detected error event"""
        try:
            # Generate unique error ID
            error_id = f"{component}_{error_type}_{int(time.time())}"

            # Determine severity and category
            severity = self._classify_error_severity(
                error_type, error_message, component
            )
            category = self._classify_error_category(
                error_type, error_message, component
            )

            # Check if this is a recurring error
            error_signature = f"{component}:{error_type}:{hash(error_message) % 10000}"

            if error_signature in self.error_events:
                # Update existing error
                existing_error = self.error_events[error_signature]
                existing_error.recurrence_count += 1
                existing_error.timestamp = datetime.now()

                # Escalate severity if recurring
                if existing_error.recurrence_count > 5:
                    severity = (
                        ErrorSeverity.HIGH
                        if severity == ErrorSeverity.MEDIUM
                        else ErrorSeverity.CRITICAL
                    )

            else:
                # Create new error event
                error_event = ErrorEvent(
                    id=error_id,
                    timestamp=datetime.now(),
                    error_type=error_type,
                    error_message=error_message,
                    stack_trace=stack_trace,
                    severity=severity,
                    category=category,
                    component=component,
                    metadata=metadata or {},
                )

                self.error_events[error_signature] = error_event

            # Store in memory for analytics
            await self.memory.store_context(
                {
                    "type": "error_event",
                    "error_id": error_id,
                    "error_type": error_type,
                    "severity": severity.value,
                    "category": category.value,
                    "component": component,
                    "message": error_message,
                    "metadata": metadata or {},
                },
                tier=MemoryTier.ANALYTICS,
            )

            # Attempt automatic recovery if not in emergency mode
            if (
                not self.emergency_mode_active
                and len(self.active_recoveries) < self.max_concurrent_recoveries
            ):
                await self._attempt_recovery(self.error_events[error_signature])

        except Exception as e:
            logger.error(f"Error processing error event: {e}")

    async def _attempt_recovery(self, error_event: ErrorEvent):
        """Attempt automatic recovery for an error"""
        try:
            # Find matching recovery rules
            matching_rules = self._find_recovery_rules(error_event)

            if not matching_rules:
                logger.warning(
                    f"No recovery rules found for error: {error_event.error_type}"
                )
                return

            # Sort by priority and success rate
            matching_rules.sort(
                key=lambda r: (r.success_rate_threshold, -len(r.actions))
            )

            for rule in matching_rules[:3]:  # Try top 3 rules
                if not self._should_apply_rule(rule):
                    continue

                recovery_task = asyncio.create_task(
                    self._execute_recovery_rule(error_event, rule)
                )

                self.active_recoveries[error_event.id] = recovery_task
                break

        except Exception as e:
            logger.error(f"Error attempting recovery for {error_event.id}: {e}")

    def _find_recovery_rules(self, error_event: ErrorEvent) -> List[RecoveryRule]:
        """Find recovery rules that match the error"""
        matching_rules = []

        for rule in self.recovery_rules:
            if not rule.enabled:
                continue

            # Check category match
            if rule.category != error_event.category:
                continue

            # Check error pattern match
            import re

            if rule.error_pattern and not re.search(
                rule.error_pattern, error_event.error_message, re.IGNORECASE
            ):
                continue

            # Check severity level
            severity_levels = {
                ErrorSeverity.LOW: 1,
                ErrorSeverity.MEDIUM: 2,
                ErrorSeverity.HIGH: 3,
                ErrorSeverity.CRITICAL: 4,
            }

            if severity_levels[error_event.severity] < severity_levels[rule.severity]:
                continue

            matching_rules.append(rule)

        return matching_rules

    def _should_apply_rule(self, rule: RecoveryRule) -> bool:
        """Check if a recovery rule should be applied"""
        # Check cooldown
        if rule.last_used:
            time_since_last = (datetime.now() - rule.last_used).total_seconds() / 60
            if time_since_last < rule.cooldown_minutes:
                return False

        # Check success rate
        total_attempts = rule.success_count + rule.failure_count
        if total_attempts >= 10:  # Need at least 10 attempts for reliable stats
            success_rate = rule.success_count / total_attempts
            if success_rate < rule.success_rate_threshold:
                return False

        return True

    async def _execute_recovery_rule(self, error_event: ErrorEvent, rule: RecoveryRule):
        """Execute a recovery rule"""
        try:
            logger.info(
                f"Executing recovery rule '{rule.name}' for error {error_event.id}"
            )

            rule.last_used = datetime.now()
            success = True

            for action in rule.actions:
                try:
                    action_success = await self._execute_recovery_action(
                        action, error_event, rule
                    )
                    if not action_success:
                        success = False
                        break

                    error_event.recovery_actions_taken.append(action.value)

                except Exception as e:
                    logger.error(f"Recovery action {action} failed: {e}")
                    success = False
                    break

            # Update rule statistics
            if success:
                rule.success_count += 1
                error_event.resolved = True
                error_event.resolution_timestamp = datetime.now()
                logger.info(f"Successfully recovered from error {error_event.id}")
            else:
                rule.failure_count += 1
                logger.warning(f"Recovery failed for error {error_event.id}")

            # Store recovery result
            await self.memory.store_context(
                {
                    "type": "recovery_attempt",
                    "error_id": error_event.id,
                    "rule_name": rule.name,
                    "actions": [a.value for a in rule.actions],
                    "success": success,
                    "timestamp": datetime.now().isoformat(),
                },
                tier=MemoryTier.ANALYTICS,
            )

        except Exception as e:
            logger.error(f"Error executing recovery rule {rule.name}: {e}")
            rule.failure_count += 1

        finally:
            # Remove from active recoveries
            if error_event.id in self.active_recoveries:
                del self.active_recoveries[error_event.id]

    async def _execute_recovery_action(
        self, action: RecoveryAction, error_event: ErrorEvent, rule: RecoveryRule
    ) -> bool:
        """Execute a specific recovery action"""
        try:
            if action == RecoveryAction.RESTART_SERVICE:
                return await self._restart_service(error_event.component)

            elif action == RecoveryAction.FAILOVER_PROVIDER:
                return await self._failover_provider(error_event)

            elif action == RecoveryAction.CLEAR_CACHE:
                return await self._clear_cache(error_event.component)

            elif action == RecoveryAction.RESET_CONNECTION:
                return await self._reset_connection(error_event.component)

            elif action == RecoveryAction.INSTALL_DEPENDENCY:
                return await self._install_dependency(error_event)

            elif action == RecoveryAction.ROLLBACK_CONFIG:
                return await self._rollback_config(error_event)

            elif action == RecoveryAction.SCALE_RESOURCES:
                return await self._scale_resources(error_event)

            elif action == RecoveryAction.SWITCH_MCP_SERVER:
                return await self._switch_mcp_server(error_event)

            elif action == RecoveryAction.EMERGENCY_MODE:
                return await self._activate_emergency_mode()

            elif action == RecoveryAction.RESTART_COMPONENT:
                return await self._restart_component(error_event.component)

            else:
                logger.warning(f"Unknown recovery action: {action}")
                return False

        except Exception as e:
            logger.error(f"Recovery action {action} failed: {e}")
            return False

    def _classify_error_severity(
        self, error_type: str, error_message: str, component: str
    ) -> ErrorSeverity:
        """Classify error severity"""
        # Critical errors
        if any(
            term in error_message.lower()
            for term in ['critical', 'fatal', 'system failure', 'crash']
        ):
            return ErrorSeverity.CRITICAL

        # High severity errors
        if any(
            term in error_message.lower()
            for term in ['connection', 'timeout', 'authentication', 'permission']
        ):
            return ErrorSeverity.HIGH

        # Medium severity errors
        if any(
            term in error_message.lower() for term in ['error', 'failed', 'exception']
        ):
            return ErrorSeverity.MEDIUM

        # Default to low severity
        return ErrorSeverity.LOW

    def _classify_error_category(
        self, error_type: str, error_message: str, component: str
    ) -> ErrorCategory:
        """Classify error category"""
        message_lower = error_message.lower()

        if 'provider' in message_lower or 'completion' in message_lower:
            return ErrorCategory.PROVIDER_FAILURE
        elif 'memory' in message_lower or 'cache' in message_lower:
            return ErrorCategory.MEMORY_SYSTEM
        elif 'mcp' in message_lower or 'server' in message_lower:
            return ErrorCategory.MCP_SERVER
        elif 'database' in message_lower or 'sql' in message_lower:
            return ErrorCategory.DATABASE_CONNECTION
        elif 'timeout' in message_lower or 'network' in message_lower:
            return ErrorCategory.NETWORK_TIMEOUT
        elif 'config' in message_lower or 'setting' in message_lower:
            return ErrorCategory.CONFIGURATION
        elif 'dependency' in message_lower or 'import' in message_lower:
            return ErrorCategory.DEPENDENCY_MISSING
        elif 'performance' in message_lower or 'slow' in message_lower:
            return ErrorCategory.PERFORMANCE_DEGRADATION
        elif 'auth' in message_lower or 'token' in message_lower:
            return ErrorCategory.AUTHENTICATION
        elif (
            'memory' in message_lower
            or 'disk' in message_lower
            or 'resource' in message_lower
        ):
            return ErrorCategory.RESOURCE_EXHAUSTION
        else:
            return ErrorCategory.CONFIGURATION  # Default category

    def _create_recovery_rules(self) -> List[RecoveryRule]:
        """Create default recovery rules"""
        return [
            # Provider failure recovery
            RecoveryRule(
                name="provider_timeout_failover",
                error_pattern=r"timeout.*provider",
                category=ErrorCategory.PROVIDER_FAILURE,
                severity=ErrorSeverity.HIGH,
                actions=[
                    RecoveryAction.FAILOVER_PROVIDER,
                    RecoveryAction.RESET_CONNECTION,
                ],
                cooldown_minutes=5,
            ),
            # Memory system recovery
            RecoveryRule(
                name="memory_cache_clear",
                error_pattern=r"memory|cache",
                category=ErrorCategory.MEMORY_SYSTEM,
                severity=ErrorSeverity.MEDIUM,
                actions=[RecoveryAction.CLEAR_CACHE, RecoveryAction.SCALE_RESOURCES],
                cooldown_minutes=10,
            ),
            # Database connection recovery
            RecoveryRule(
                name="database_reconnect",
                error_pattern=r"database|connection.*lost",
                category=ErrorCategory.DATABASE_CONNECTION,
                severity=ErrorSeverity.HIGH,
                actions=[
                    RecoveryAction.RESET_CONNECTION,
                    RecoveryAction.RESTART_SERVICE,
                ],
                cooldown_minutes=5,
            ),
            # MCP server recovery
            RecoveryRule(
                name="mcp_server_switch",
                error_pattern=r"mcp.*server|tool.*failed",
                category=ErrorCategory.MCP_SERVER,
                severity=ErrorSeverity.MEDIUM,
                actions=[
                    RecoveryAction.SWITCH_MCP_SERVER,
                    RecoveryAction.RESTART_COMPONENT,
                ],
                cooldown_minutes=15,
            ),
            # Performance degradation recovery
            RecoveryRule(
                name="performance_optimization",
                error_pattern=r"slow|performance|degradation",
                category=ErrorCategory.PERFORMANCE_DEGRADATION,
                severity=ErrorSeverity.MEDIUM,
                actions=[RecoveryAction.SCALE_RESOURCES, RecoveryAction.CLEAR_CACHE],
                cooldown_minutes=20,
            ),
            # Critical system recovery
            RecoveryRule(
                name="critical_emergency_mode",
                error_pattern=r"critical|fatal|system.*failure",
                category=ErrorCategory.PROVIDER_FAILURE,  # Any category for critical errors
                severity=ErrorSeverity.CRITICAL,
                actions=[RecoveryAction.EMERGENCY_MODE, RecoveryAction.ROLLBACK_CONFIG],
                cooldown_minutes=30,
                max_attempts=1,
            ),
        ]

    # Recovery action implementations
    async def _restart_service(self, component: str) -> bool:
        """Restart a service component"""
        logger.info(f"Restarting service component: {component}")
        # Implementation would restart the specific component
        await asyncio.sleep(1)  # Simulate restart
        return True

    async def _failover_provider(self, error_event: ErrorEvent) -> bool:
        """Failover to a different provider"""
        logger.info("Executing provider failover")
        # Implementation would switch to backup provider
        return True

    async def _clear_cache(self, component: str) -> bool:
        """Clear cache for component"""
        logger.info(f"Clearing cache for component: {component}")
        try:
            await self.memory.clear_cache_tier("session")
            return True
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False

    async def _reset_connection(self, component: str) -> bool:
        """Reset connections for component"""
        logger.info(f"Resetting connections for component: {component}")
        # Implementation would reset specific connections
        return True

    async def _install_dependency(self, error_event: ErrorEvent) -> bool:
        """Install missing dependency"""
        logger.info("Installing missing dependency")
        # Implementation would install missing packages
        return True

    async def _rollback_config(self, error_event: ErrorEvent) -> bool:
        """Rollback recent configuration changes"""
        logger.info("Rolling back configuration")
        # Implementation would rollback to last known good config
        return True

    async def _scale_resources(self, error_event: ErrorEvent) -> bool:
        """Scale system resources"""
        logger.info("Scaling system resources")
        # Implementation would scale CPU/memory/concurrency
        return True

    async def _switch_mcp_server(self, error_event: ErrorEvent) -> bool:
        """Switch to alternative MCP server"""
        logger.info("Switching MCP server")
        # Implementation would switch to backup MCP server
        return True

    async def _activate_emergency_mode(self) -> bool:
        """Activate emergency mode"""
        logger.warning("Activating emergency mode")
        self.emergency_mode_active = True

        # Emergency actions:
        # 1. Switch to local-only providers
        # 2. Reduce functionality to core features
        # 3. Increase monitoring
        # 4. Send alerts

        return True

    async def _restart_component(self, component: str) -> bool:
        """Restart specific component"""
        logger.info(f"Restarting component: {component}")
        # Implementation would restart the specific component
        return True

    async def get_error_recovery_status(self) -> Dict[str, Any]:
        """Get current error recovery status"""
        return {
            "emergency_mode_active": self.emergency_mode_active,
            "total_errors": len(self.error_events),
            "resolved_errors": len(
                [e for e in self.error_events.values() if e.resolved]
            ),
            "active_recoveries": len(self.active_recoveries),
            "component_health": self.component_health,
            "recovery_rules": len([r for r in self.recovery_rules if r.enabled]),
            "recent_errors": [
                {
                    "id": e.id,
                    "type": e.error_type,
                    "severity": e.severity.value,
                    "resolved": e.resolved,
                    "timestamp": e.timestamp.isoformat(),
                }
                for e in sorted(
                    self.error_events.values(), key=lambda x: x.timestamp, reverse=True
                )[:10]
            ],
        }
