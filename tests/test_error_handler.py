"""
Tests for Error Handler
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
from datetime import datetime

from app.agent.error_handler import (
    ErrorHandler, RetryStrategy, DegradationLevel, RetryConfig, DegradationConfig, ErrorStats
)
from app.agent.exceptions import (
    MultiAgentError, ErrorCategory, ErrorSeverity,
    NetworkError, ModelAPIError, ConfigurationError, ValidationError
)


class TestRetryConfig:
    """Test RetryConfig data class"""
    
    def test_retry_config_creation(self):
        """Test RetryConfig creation"""
        config = RetryConfig(
            max_attempts=5,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            base_delay=2.0,
            max_delay=60.0,
            backoff_factor=2.5,
            jitter=True
        )
        
        assert config.max_attempts == 5
        assert config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert config.base_delay == 2.0
        assert config.max_delay == 60.0
        assert config.backoff_factor == 2.5
        assert config.jitter is True
    
    def test_retry_config_defaults(self):
        """Test RetryConfig with defaults"""
        config = RetryConfig()
        
        assert config.max_attempts == 3
        assert config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.backoff_factor == 2.0
        assert config.jitter is True


class TestDegradationConfig:
    """Test DegradationConfig data class"""
    
    def test_degradation_config_creation(self):
        """Test DegradationConfig creation"""
        config = DegradationConfig(
            enabled=True,
            error_rate_threshold=0.3,
            recovery_time=300.0,
            level=DegradationLevel.PARTIAL
        )
        
        assert config.enabled is True
        assert config.error_rate_threshold == 0.3
        assert config.recovery_time == 300.0
        assert config.level == DegradationLevel.PARTIAL
    
    def test_degradation_config_defaults(self):
        """Test DegradationConfig with defaults"""
        config = DegradationConfig()
        
        assert config.enabled is True
        assert config.error_rate_threshold == 0.2
        assert config.recovery_time == 600.0
        assert config.level == DegradationLevel.PARTIAL


class TestErrorStats:
    """Test ErrorStats data class"""
    
    def test_error_stats_creation(self):
        """Test ErrorStats creation"""
        stats = ErrorStats(
            total_errors=10,
            error_rate=0.15,
            recent_errors=[],
            category_counts={"network": 5, "api": 3},
            severity_counts={"high": 2, "medium": 6}
        )
        
        assert stats.total_errors == 10
        assert stats.error_rate == 0.15
        assert stats.recent_errors == []
        assert stats.category_counts["network"] == 5
        assert stats.severity_counts["high"] == 2
    
    def test_error_stats_defaults(self):
        """Test ErrorStats with defaults"""
        stats = ErrorStats()
        
        assert stats.total_errors == 0
        assert stats.error_rate == 0.0
        assert stats.recent_errors == []
        assert stats.category_counts == {}
        assert stats.severity_counts == {}


class TestErrorHandler:
    """Test ErrorHandler functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.error_handler = ErrorHandler()
    
    def test_initialization(self):
        """Test error handler initialization"""
        assert self.error_handler.retry_config is not None
        assert self.error_handler.degradation_config is not None
        assert self.error_handler.stats is not None
        assert self.error_handler.degradation_active is False
        assert self.error_handler.degradation_start_time is None
    
    def test_initialization_with_custom_configs(self):
        """Test error handler initialization with custom configs"""
        retry_config = RetryConfig(max_attempts=5)
        degradation_config = DegradationConfig(enabled=False)
        
        handler = ErrorHandler(retry_config, degradation_config)
        
        assert handler.retry_config.max_attempts == 5
        assert handler.degradation_config.enabled is False
    
    def test_setup_default_configs(self):
        """Test default configuration setup"""
        # Check that category-specific configs are set up
        assert ErrorCategory.NETWORK in self.error_handler.retry_config.category_configs
        assert ErrorCategory.MODEL_API in self.error_handler.retry_config.category_configs
        assert ErrorCategory.RATE_LIMIT in self.error_handler.retry_config.category_configs
        
        # Check network config
        network_config = self.error_handler.retry_config.category_configs[ErrorCategory.NETWORK]
        assert network_config.max_attempts == 5
        assert network_config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        
        # Check configuration config (no retry)
        config_config = self.error_handler.retry_config.category_configs[ErrorCategory.CONFIGURATION]
        assert config_config.max_attempts == 1
        assert config_config.strategy == RetryStrategy.NO_RETRY
    
    def test_should_retry_recoverable_error(self):
        """Test should_retry for recoverable error"""
        error = NetworkError("Connection failed")
        
        # First attempt should allow retry
        assert self.error_handler.should_retry(error, 1) is True
        
        # Within max attempts should allow retry
        assert self.error_handler.should_retry(error, 3) is True
        
        # Beyond max attempts should not allow retry
        assert self.error_handler.should_retry(error, 6) is False
    
    def test_should_retry_non_recoverable_error(self):
        """Test should_retry for non-recoverable error"""
        error = ConfigurationError("Invalid config")
        error.recoverable = False
        
        # Non-recoverable errors should never retry
        assert self.error_handler.should_retry(error, 1) is False
    
    def test_should_retry_no_retry_strategy(self):
        """Test should_retry with NO_RETRY strategy"""
        error = ConfigurationError("Invalid config")
        
        # Configuration errors have NO_RETRY strategy
        assert self.error_handler.should_retry(error, 1) is False
    
    def test_should_degrade_disabled(self):
        """Test should_degrade when degradation is disabled"""
        self.error_handler.degradation_config.enabled = False
        
        assert self.error_handler.should_degrade() is False
    
    def test_should_degrade_high_error_rate(self):
        """Test should_degrade with high error rate"""
        self.error_handler.degradation_config.enabled = True
        self.error_handler.degradation_config.error_rate_threshold = 0.1
        self.error_handler.stats.error_rate = 0.2
        
        assert self.error_handler.should_degrade() is True
    
    def test_should_degrade_critical_errors(self):
        """Test should_degrade with multiple critical errors"""
        self.error_handler.degradation_config.enabled = True
        self.error_handler.stats.error_rate = 0.05  # Below threshold
        
        # Add critical errors
        critical_errors = []
        for i in range(3):
            error = MultiAgentError(
                f"Critical error {i}",
                severity=ErrorSeverity.CRITICAL
            )
            critical_errors.append(error)
        
        # Add some non-critical errors
        for i in range(7):
            error = MultiAgentError(
                f"Normal error {i}",
                severity=ErrorSeverity.MEDIUM
            )
            critical_errors.append(error)
        
        self.error_handler.stats.recent_errors = critical_errors
        
        assert self.error_handler.should_degrade() is True
    
    def test_should_degrade_no_trigger(self):
        """Test should_degrade when no degradation triggers are met"""
        self.error_handler.degradation_config.enabled = True
        self.error_handler.stats.error_rate = 0.05  # Below threshold
        self.error_handler.stats.recent_errors = []
        
        assert self.error_handler.should_degrade() is False
    
    @pytest.mark.asyncio
    async def test_handle_error_basic(self):
        """Test basic error handling"""
        error = NetworkError("Connection timeout")
        context = {"operation": "test_op", "component": "test_component"}
        
        with patch.object(self.error_handler, '_record_error') as mock_record:
            with patch.object(self.error_handler, '_get_recovery_action') as mock_recovery:
                mock_recovery.return_value = "retry"
                
                result = await self.error_handler.handle_error(error, context)
                
                mock_record.assert_called_once_with(error, context)
                assert result is not None
    
    def test_get_retry_delay_exponential_backoff(self):
        """Test retry delay calculation for exponential backoff"""
        config = RetryConfig(
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            base_delay=1.0,
            backoff_factor=2.0,
            max_delay=10.0,
            jitter=False
        )
        
        # Test different attempts
        delay1 = self.error_handler._get_retry_delay(config, 1)
        delay2 = self.error_handler._get_retry_delay(config, 2)
        delay3 = self.error_handler._get_retry_delay(config, 3)
        
        assert delay1 == 1.0  # base_delay
        assert delay2 == 2.0  # base_delay * backoff_factor
        assert delay3 == 4.0  # base_delay * backoff_factor^2
    
    def test_get_retry_delay_fixed_interval(self):
        """Test retry delay calculation for fixed interval"""
        config = RetryConfig(
            strategy=RetryStrategy.FIXED_INTERVAL,
            base_delay=5.0,
            jitter=False
        )
        
        # All attempts should have same delay
        delay1 = self.error_handler._get_retry_delay(config, 1)
        delay2 = self.error_handler._get_retry_delay(config, 2)
        delay3 = self.error_handler._get_retry_delay(config, 3)
        
        assert delay1 == 5.0
        assert delay2 == 5.0
        assert delay3 == 5.0
    
    def test_get_retry_delay_linear_backoff(self):
        """Test retry delay calculation for linear backoff"""
        config = RetryConfig(
            strategy=RetryStrategy.LINEAR_BACKOFF,
            base_delay=2.0,
            jitter=False
        )
        
        delay1 = self.error_handler._get_retry_delay(config, 1)
        delay2 = self.error_handler._get_retry_delay(config, 2)
        delay3 = self.error_handler._get_retry_delay(config, 3)
        
        assert delay1 == 2.0  # base_delay * 1
        assert delay2 == 4.0  # base_delay * 2
        assert delay3 == 6.0  # base_delay * 3
    
    def test_get_retry_delay_max_delay_limit(self):
        """Test retry delay respects max_delay limit"""
        config = RetryConfig(
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            base_delay=10.0,
            backoff_factor=3.0,
            max_delay=20.0,
            jitter=False
        )
        
        delay1 = self.error_handler._get_retry_delay(config, 1)
        delay2 = self.error_handler._get_retry_delay(config, 2)
        delay3 = self.error_handler._get_retry_delay(config, 3)
        
        assert delay1 == 10.0
        assert delay2 == 20.0  # Would be 30.0, but capped at max_delay
        assert delay3 == 20.0  # Would be 90.0, but capped at max_delay
    
    def test_get_retry_delay_with_jitter(self):
        """Test retry delay with jitter"""
        config = RetryConfig(
            strategy=RetryStrategy.FIXED_INTERVAL,
            base_delay=10.0,
            jitter=True
        )
        
        # With jitter, delay should vary around base delay
        delays = []
        for _ in range(10):
            delay = self.error_handler._get_retry_delay(config, 1)
            delays.append(delay)
        
        # All delays should be different (with high probability)
        assert len(set(delays)) > 1
        
        # All delays should be within reasonable range of base delay
        for delay in delays:
            assert 5.0 <= delay <= 15.0  # Roughly base_delay ± 50%
    
    def test_record_error(self):
        """Test error recording"""
        error = NetworkError("Connection failed")
        context = {"operation": "test_op"}
        
        initial_count = self.error_handler.stats.total_errors
        
        self.error_handler._record_error(error, context)
        
        assert self.error_handler.stats.total_errors == initial_count + 1
        assert ErrorCategory.NETWORK.value in self.error_handler.stats.category_counts
        assert ErrorSeverity.MEDIUM.value in self.error_handler.stats.severity_counts
    
    def test_get_recovery_action_network_error(self):
        """Test recovery action for network error"""
        error = NetworkError("Connection timeout")
        
        action = self.error_handler._get_recovery_action(error)
        
        assert action in ["retry", "fallback", "degrade"]
    
    def test_get_recovery_action_configuration_error(self):
        """Test recovery action for configuration error"""
        error = ConfigurationError("Invalid config")
        
        action = self.error_handler._get_recovery_action(error)
        
        assert action in ["fix_config", "use_default", "fail"]
    
    def test_get_recovery_action_rate_limit_error(self):
        """Test recovery action for rate limit error"""
        error = ModelAPIError("Rate limit exceeded", status_code=429)
        error.category = ErrorCategory.RATE_LIMIT
        
        action = self.error_handler._get_recovery_action(error)
        
        assert action in ["wait", "use_cache", "degrade"]
    
    @pytest.mark.asyncio
    async def test_retry_with_backoff_success(self):
        """Test retry with backoff - successful after retries"""
        call_count = 0
        
        async def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise NetworkError("Connection failed")
            return "success"
        
        config = RetryConfig(max_attempts=3, base_delay=0.01)  # Fast for testing
        
        result = await self.error_handler.retry_with_backoff(failing_operation, config)
        
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_with_backoff_max_attempts(self):
        """Test retry with backoff - max attempts exceeded"""
        async def always_failing_operation():
            raise NetworkError("Always fails")
        
        config = RetryConfig(max_attempts=2, base_delay=0.01)
        
        with pytest.raises(NetworkError):
            await self.error_handler.retry_with_backoff(always_failing_operation, config)
    
    @pytest.mark.asyncio
    async def test_retry_with_backoff_no_retry_strategy(self):
        """Test retry with NO_RETRY strategy"""
        async def failing_operation():
            raise ConfigurationError("Config error")
        
        config = RetryConfig(strategy=RetryStrategy.NO_RETRY)
        
        with pytest.raises(ConfigurationError):
            await self.error_handler.retry_with_backoff(failing_operation, config)
    
    def test_activate_degradation(self):
        """Test degradation activation"""
        assert self.error_handler.degradation_active is False
        
        self.error_handler._activate_degradation()
        
        assert self.error_handler.degradation_active is True
        assert self.error_handler.degradation_start_time is not None
    
    def test_deactivate_degradation(self):
        """Test degradation deactivation"""
        self.error_handler._activate_degradation()
        assert self.error_handler.degradation_active is True
        
        self.error_handler._deactivate_degradation()
        
        assert self.error_handler.degradation_active is False
        assert self.error_handler.degradation_start_time is None
    
    def test_should_recover_from_degradation(self):
        """Test recovery from degradation"""
        # Activate degradation
        self.error_handler._activate_degradation()
        
        # Set low error rate
        self.error_handler.stats.error_rate = 0.05
        self.error_handler.stats.recent_errors = []
        
        # Should recover if error rate is low and no recent critical errors
        assert self.error_handler._should_recover_from_degradation() is True
    
    def test_should_not_recover_from_degradation(self):
        """Test not recovering from degradation when conditions not met"""
        # Activate degradation
        self.error_handler._activate_degradation()
        
        # Set high error rate
        self.error_handler.stats.error_rate = 0.3
        
        # Should not recover if error rate is still high
        assert self.error_handler._should_recover_from_degradation() is False
    
    def test_get_error_summary(self):
        """Test getting error summary"""
        # Add some test data
        self.error_handler.stats.total_errors = 10
        self.error_handler.stats.category_counts = {
            ErrorCategory.NETWORK.value: 5,
            ErrorCategory.MODEL_API.value: 3,
            ErrorCategory.VALIDATION.value: 2
        }
        self.error_handler.stats.severity_counts = {
            ErrorSeverity.HIGH.value: 2,
            ErrorSeverity.MEDIUM.value: 6,
            ErrorSeverity.LOW.value: 2
        }
        
        summary = self.error_handler.get_error_summary()
        
        assert summary["total_errors"] == 10
        assert summary["category_breakdown"][ErrorCategory.NETWORK.value] == 5
        assert summary["severity_breakdown"][ErrorSeverity.HIGH.value] == 2
        assert summary["degradation_active"] is False
    
    def test_reset_stats(self):
        """Test resetting error statistics"""
        # Add some test data
        self.error_handler.stats.total_errors = 10
        self.error_handler.stats.error_rate = 0.2
        self.error_handler.stats.category_counts = {"network": 5}
        
        self.error_handler.reset_stats()
        
        assert self.error_handler.stats.total_errors == 0
        assert self.error_handler.stats.error_rate == 0.0
        assert self.error_handler.stats.category_counts == {}
        assert self.error_handler.stats.severity_counts == {}
        assert self.error_handler.stats.recent_errors == []


class TestRetryStrategy:
    """Test RetryStrategy enum"""
    
    def test_retry_strategy_values(self):
        """Test RetryStrategy enum values"""
        assert RetryStrategy.EXPONENTIAL_BACKOFF == "exponential_backoff"
        assert RetryStrategy.FIXED_INTERVAL == "fixed_interval"
        assert RetryStrategy.LINEAR_BACKOFF == "linear_backoff"
        assert RetryStrategy.NO_RETRY == "no_retry"


class TestDegradationLevel:
    """Test DegradationLevel enum"""
    
    def test_degradation_level_values(self):
        """Test DegradationLevel enum values"""
        assert DegradationLevel.NONE == "none"
        assert DegradationLevel.PARTIAL == "partial"
        assert DegradationLevel.FALLBACK == "fallback"
        assert DegradationLevel.MINIMAL == "minimal"