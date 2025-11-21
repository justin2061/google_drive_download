"""
重試管理器測試
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

from src.core.retry_manager import (
    RetryManager,
    RetryStrategy,
    ErrorCategory,
    RetryResult,
    retry,
    quick_retry,
    default_retry_manager
)
from googleapiclient.errors import HttpError


class TestRetryStrategy:
    """測試重試策略枚舉"""

    def test_strategy_values(self):
        """測試策略值"""
        assert RetryStrategy.FIXED.value == "fixed"
        assert RetryStrategy.EXPONENTIAL.value == "exponential"
        assert RetryStrategy.LINEAR.value == "linear"
        assert RetryStrategy.RANDOM.value == "random"


class TestErrorCategory:
    """測試錯誤分類枚舉"""

    def test_category_values(self):
        """測試分類值"""
        assert ErrorCategory.NETWORK.value == "network"
        assert ErrorCategory.AUTH.value == "auth"
        assert ErrorCategory.RATE_LIMIT.value == "rate_limit"
        assert ErrorCategory.SERVER.value == "server"
        assert ErrorCategory.CLIENT.value == "client"
        assert ErrorCategory.UNKNOWN.value == "unknown"


class TestRetryResult:
    """測試重試結果類別"""

    def test_success_result(self):
        """測試成功結果"""
        result = RetryResult(success=True, result="test_data", attempts=1, total_time=0.5)

        assert result.success is True
        assert result.result == "test_data"
        assert result.attempts == 1
        assert result.total_time == 0.5
        assert result.error is None
        assert bool(result) is True

    def test_failure_result(self):
        """測試失敗結果"""
        error = Exception("test error")
        result = RetryResult(success=False, error=error, attempts=3, total_time=5.0)

        assert result.success is False
        assert result.result is None
        assert result.error == error
        assert result.attempts == 3
        assert bool(result) is False


class TestRetryManager:
    """測試重試管理器"""

    def setup_method(self):
        """測試前設定"""
        self.manager = RetryManager(
            max_retries=3,
            base_delay=0.1,  # 使用短延遲加速測試
            max_delay=1.0,
            strategy=RetryStrategy.EXPONENTIAL,
            jitter=False  # 禁用抖動以便測試
        )

    def test_init(self):
        """測試初始化"""
        assert self.manager.max_retries == 3
        assert self.manager.base_delay == 0.1
        assert self.manager.max_delay == 1.0
        assert self.manager.strategy == RetryStrategy.EXPONENTIAL
        assert self.manager.jitter is False

    def test_classify_error_network(self):
        """測試網路錯誤分類"""
        error = ConnectionError("Network error")
        category = self.manager.classify_error(error)
        assert category == ErrorCategory.NETWORK

    def test_classify_error_timeout(self):
        """測試超時錯誤分類"""
        error = TimeoutError("Timeout")
        category = self.manager.classify_error(error)
        assert category == ErrorCategory.NETWORK

    def test_classify_error_unknown(self):
        """測試未知錯誤分類"""
        error = ValueError("Unknown error")
        category = self.manager.classify_error(error)
        assert category == ErrorCategory.UNKNOWN

    @patch('src.core.retry_manager.HttpError')
    def test_classify_http_429_error(self, mock_http_error):
        """測試 HTTP 429 錯誤分類"""
        mock_resp = Mock()
        mock_resp.status = 429
        error = HttpError(mock_resp, b"Rate limit")

        category = self.manager.classify_error(error)
        assert category == ErrorCategory.RATE_LIMIT

    @patch('src.core.retry_manager.HttpError')
    def test_classify_http_500_error(self, mock_http_error):
        """測試 HTTP 500 錯誤分類"""
        mock_resp = Mock()
        mock_resp.status = 500
        error = HttpError(mock_resp, b"Server error")

        category = self.manager.classify_error(error)
        assert category == ErrorCategory.SERVER

    def test_is_retryable_network_error(self):
        """測試網路錯誤是否可重試"""
        error = ConnectionError("Network error")
        assert self.manager.is_retryable(error) is True

    def test_is_retryable_timeout_error(self):
        """測試超時錯誤是否可重試"""
        error = TimeoutError("Timeout")
        assert self.manager.is_retryable(error) is True

    def test_is_retryable_value_error(self):
        """測試一般錯誤不可重試"""
        error = ValueError("Invalid value")
        assert self.manager.is_retryable(error) is False

    def test_calculate_delay_fixed(self):
        """測試固定延遲計算"""
        manager = RetryManager(
            strategy=RetryStrategy.FIXED,
            base_delay=1.0,
            jitter=False
        )

        assert manager.calculate_delay(0) == 1.0
        assert manager.calculate_delay(1) == 1.0
        assert manager.calculate_delay(5) == 1.0

    def test_calculate_delay_exponential(self):
        """測試指數退避延遲計算"""
        manager = RetryManager(
            strategy=RetryStrategy.EXPONENTIAL,
            base_delay=1.0,
            backoff_factor=2.0,
            max_delay=60.0,
            jitter=False
        )

        assert manager.calculate_delay(0) == 1.0
        assert manager.calculate_delay(1) == 2.0
        assert manager.calculate_delay(2) == 4.0
        assert manager.calculate_delay(3) == 8.0

    def test_calculate_delay_linear(self):
        """測試線性延遲計算"""
        manager = RetryManager(
            strategy=RetryStrategy.LINEAR,
            base_delay=1.0,
            jitter=False
        )

        assert manager.calculate_delay(0) == 1.0
        assert manager.calculate_delay(1) == 2.0
        assert manager.calculate_delay(2) == 3.0

    def test_calculate_delay_max_limit(self):
        """測試延遲最大值限制"""
        manager = RetryManager(
            strategy=RetryStrategy.EXPONENTIAL,
            base_delay=1.0,
            max_delay=5.0,
            backoff_factor=10.0,
            jitter=False
        )

        assert manager.calculate_delay(5) == 5.0  # 應該被限制在 max_delay

    def test_retry_sync_success_first_attempt(self):
        """測試同步重試 - 首次成功"""
        mock_func = Mock(return_value="success")

        result = self.manager.retry_sync(mock_func)

        assert result.success is True
        assert result.result == "success"
        assert result.attempts == 1
        mock_func.assert_called_once()

    def test_retry_sync_success_after_retry(self):
        """測試同步重試 - 重試後成功"""
        mock_func = Mock(side_effect=[
            ConnectionError("First failure"),
            "success"
        ])

        result = self.manager.retry_sync(mock_func)

        assert result.success is True
        assert result.result == "success"
        assert result.attempts == 2
        assert mock_func.call_count == 2

    def test_retry_sync_all_retries_fail(self):
        """測試同步重試 - 所有重試失敗"""
        error = ConnectionError("Persistent failure")
        mock_func = Mock(side_effect=error)

        result = self.manager.retry_sync(mock_func)

        assert result.success is False
        assert result.error == error
        assert result.attempts == 4  # 1 initial + 3 retries
        assert mock_func.call_count == 4

    def test_retry_sync_non_retryable_error(self):
        """測試同步重試 - 不可重試的錯誤"""
        error = ValueError("Non-retryable error")
        mock_func = Mock(side_effect=error)

        result = self.manager.retry_sync(mock_func)

        assert result.success is False
        assert result.error == error
        assert result.attempts == 1  # 只嘗試一次
        mock_func.assert_called_once()

    def test_retry_sync_with_args(self):
        """測試同步重試 - 帶參數"""
        mock_func = Mock(return_value="success")

        result = self.manager.retry_sync(mock_func, "arg1", "arg2", key="value")

        assert result.success is True
        mock_func.assert_called_once_with("arg1", "arg2", key="value")

    def test_retry_sync_custom_max_retries(self):
        """測試同步重試 - 自訂重試次數"""
        error = ConnectionError("Failure")
        mock_func = Mock(side_effect=error)

        result = self.manager.retry_sync(mock_func, max_retries=1)

        assert result.success is False
        assert result.attempts == 2  # 1 initial + 1 retry

    def test_retry_sync_custom_exceptions(self):
        """測試同步重試 - 自訂可重試例外"""
        error = ValueError("Custom error")
        mock_func = Mock(side_effect=[error, "success"])

        result = self.manager.retry_sync(
            mock_func,
            custom_exceptions=(ValueError,)
        )

        assert result.success is True
        assert result.attempts == 2

    @pytest.mark.asyncio
    async def test_retry_async_success(self):
        """測試異步重試成功"""
        async def async_func():
            return "async_success"

        result = await self.manager.retry_async(async_func)

        assert result.success is True
        assert result.result == "async_success"

    @pytest.mark.asyncio
    async def test_retry_async_with_retry(self):
        """測試異步重試 - 重試後成功"""
        call_count = 0

        async def async_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Async failure")
            return "async_success"

        result = await self.manager.retry_async(async_func)

        assert result.success is True
        assert result.result == "async_success"
        assert result.attempts == 2

    def test_get_stats(self):
        """測試統計資訊"""
        # 執行一些操作
        self.manager.retry_sync(lambda: "success")
        self.manager.retry_sync(Mock(side_effect=ValueError("error")))

        stats = self.manager.get_stats()

        assert stats['total_calls'] >= 2
        assert 'successful_calls' in stats
        assert 'failed_calls' in stats
        assert 'success_rate' in stats
        assert 'config' in stats

    def test_reset_stats(self):
        """測試重置統計"""
        self.manager.retry_sync(lambda: "success")
        self.manager.reset_stats()

        stats = self.manager.get_stats()

        assert stats['total_calls'] == 0
        assert stats['successful_calls'] == 0
        assert stats['failed_calls'] == 0


class TestRetryDecorator:
    """測試重試裝飾器"""

    def test_retry_decorator_success(self):
        """測試裝飾器成功執行"""
        @retry(max_retries=2, base_delay=0.1)
        def test_func():
            return "decorated_success"

        result = test_func()
        assert result == "decorated_success"

    def test_retry_decorator_with_retry(self):
        """測試裝飾器重試"""
        call_count = 0

        @retry(max_retries=3, base_delay=0.1)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Failure")
            return "success_after_retry"

        result = test_func()
        assert result == "success_after_retry"
        assert call_count == 2

    def test_retry_decorator_failure(self):
        """測試裝飾器最終失敗"""
        @retry(max_retries=2, base_delay=0.1)
        def test_func():
            raise ConnectionError("Persistent failure")

        with pytest.raises(ConnectionError):
            test_func()


class TestQuickRetry:
    """測試快速重試函數"""

    def test_quick_retry_success(self):
        """測試快速重試成功"""
        result = quick_retry(lambda: "quick_success")
        assert result == "quick_success"

    def test_quick_retry_failure(self):
        """測試快速重試失敗"""
        with pytest.raises(ValueError):
            quick_retry(Mock(side_effect=ValueError("Quick failure")))


class TestDefaultRetryManager:
    """測試預設重試管理器"""

    def test_default_manager_exists(self):
        """測試預設管理器存在"""
        assert default_retry_manager is not None
        assert isinstance(default_retry_manager, RetryManager)


if __name__ == '__main__':
    pytest.main([__file__])
