"""
自定義例外類別測試
"""

import pytest
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

from src.utils.exceptions import (
    DownloadError,
    NetworkError,
    AuthenticationError,
    QuotaExceededError,
    FileNotFoundError,
    FilePermissionError,
    ConfigurationError,
    ValidationError,
    RetryableError,
    FatalError,
    is_retryable_error,
    get_retry_delay,
    create_error_context
)


class TestDownloadError:
    """測試下載錯誤基類"""

    def test_basic_init(self):
        """測試基本初始化"""
        error = DownloadError("Test error")

        assert str(error) == "Test error"
        assert error.error_type == "DownloadError"
        assert error.file_id is None
        assert error.details == {}

    def test_init_with_file_id(self):
        """測試帶檔案 ID 的初始化"""
        error = DownloadError("Test error", file_id="test_file_123")

        assert "test_file_123" in str(error)
        assert error.file_id == "test_file_123"

    def test_init_with_details(self):
        """測試帶詳細資訊的初始化"""
        details = {"key": "value", "count": 42}
        error = DownloadError("Test error", details=details)

        assert error.details == details

    def test_init_with_error_type(self):
        """測試自訂錯誤類型"""
        error = DownloadError("Test error", error_type="CustomType")

        assert error.error_type == "CustomType"


class TestNetworkError:
    """測試網路錯誤"""

    def test_basic_init(self):
        """測試基本初始化"""
        error = NetworkError("Network failure")

        assert str(error) == "Network failure"
        assert error.status_code is None

    def test_init_with_status_code(self):
        """測試帶狀態碼的初始化"""
        error = NetworkError("HTTP error", status_code=503)

        assert error.status_code == 503

    def test_inheritance(self):
        """測試繼承關係"""
        error = NetworkError("Network error")

        assert isinstance(error, DownloadError)
        assert isinstance(error, Exception)


class TestAuthenticationError:
    """測試認證錯誤"""

    def test_basic_init(self):
        """測試基本初始化"""
        error = AuthenticationError("Auth failed")

        assert str(error) == "Auth failed"
        assert isinstance(error, DownloadError)


class TestQuotaExceededError:
    """測試配額超限錯誤"""

    def test_default_message(self):
        """測試預設訊息"""
        error = QuotaExceededError()

        assert "配額已超限" in str(error)

    def test_custom_message(self):
        """測試自訂訊息"""
        error = QuotaExceededError("Custom quota message")

        assert str(error) == "Custom quota message"


class TestFileNotFoundError:
    """測試檔案不存在錯誤"""

    def test_init_with_file_id(self):
        """測試必須提供檔案 ID"""
        error = FileNotFoundError("test_file_123")

        assert error.file_id == "test_file_123"
        assert "test_file_123" in str(error)

    def test_custom_message(self):
        """測試自訂訊息"""
        error = FileNotFoundError("abc123", message="File is gone")

        assert "File is gone" in str(error)
        assert error.file_id == "abc123"


class TestFilePermissionError:
    """測試檔案權限錯誤"""

    def test_init_with_file_id(self):
        """測試必須提供檔案 ID"""
        error = FilePermissionError("test_file_123")

        assert error.file_id == "test_file_123"
        assert "test_file_123" in str(error)

    def test_default_message(self):
        """測試預設訊息"""
        error = FilePermissionError("abc123")

        assert "權限" in str(error)


class TestConfigurationError:
    """測試配置錯誤"""

    def test_init_with_config_key(self):
        """測試必須提供配置鍵"""
        error = ConfigurationError("api_key")

        assert error.config_key == "api_key"
        assert "api_key" in str(error)

    def test_custom_message(self):
        """測試自訂訊息"""
        error = ConfigurationError("timeout", message="Invalid timeout value")

        assert "Invalid timeout value" in str(error)


class TestValidationError:
    """測試驗證錯誤"""

    def test_init_with_field_and_value(self):
        """測試必須提供欄位和值"""
        error = ValidationError("email", "invalid@")

        assert error.field == "email"
        assert error.value == "invalid@"

    def test_default_message(self):
        """測試預設訊息"""
        error = ValidationError("count", -1)

        assert "驗證失敗" in str(error) or "count" in str(error)

    def test_custom_message(self):
        """測試自訂訊息"""
        error = ValidationError("age", -5, message="Age cannot be negative")

        assert "Age cannot be negative" in str(error)


class TestRetryableError:
    """測試可重試錯誤"""

    def test_basic_init(self):
        """測試基本初始化"""
        error = RetryableError("Temporary failure")

        assert str(error) == "Temporary failure"
        assert error.retry_after is None

    def test_init_with_retry_after(self):
        """測試帶重試間隔的初始化"""
        error = RetryableError("Rate limited", retry_after=30.0)

        assert error.retry_after == 30.0


class TestFatalError:
    """測試致命錯誤"""

    def test_basic_init(self):
        """測試基本初始化"""
        error = FatalError("Critical failure")

        assert str(error) == "Critical failure"
        assert isinstance(error, DownloadError)


class TestIsRetryableError:
    """測試 is_retryable_error 函數"""

    def test_fatal_error_not_retryable(self):
        """測試致命錯誤不可重試"""
        error = FatalError("Fatal")

        assert is_retryable_error(error) is False

    def test_retryable_error_is_retryable(self):
        """測試可重試錯誤可重試"""
        error = RetryableError("Temporary")

        assert is_retryable_error(error) is True

    def test_network_error_is_retryable(self):
        """測試網路錯誤可重試"""
        error = NetworkError("Network failure")

        assert is_retryable_error(error) is True

    def test_quota_exceeded_is_retryable(self):
        """測試配額錯誤可重試"""
        error = QuotaExceededError()

        assert is_retryable_error(error) is True

    def test_auth_error_not_retryable(self):
        """測試認證錯誤不可重試"""
        error = AuthenticationError("Auth failed")

        assert is_retryable_error(error) is False

    def test_generic_error_is_retryable(self):
        """測試一般錯誤預設可重試"""
        error = DownloadError("Generic error")

        assert is_retryable_error(error) is True


class TestGetRetryDelay:
    """測試 get_retry_delay 函數"""

    def test_default_delay(self):
        """測試預設延遲"""
        error = DownloadError("Error")

        assert get_retry_delay(error) == 1.0

    def test_retryable_error_with_retry_after(self):
        """測試可重試錯誤的 retry_after"""
        error = RetryableError("Temporary", retry_after=45.0)

        assert get_retry_delay(error) == 45.0

    def test_quota_exceeded_delay(self):
        """測試配額錯誤的延遲"""
        error = QuotaExceededError()

        assert get_retry_delay(error) == 60.0

    def test_network_error_429_delay(self):
        """測試 HTTP 429 錯誤的延遲"""
        error = NetworkError("Too many requests", status_code=429)

        assert get_retry_delay(error) == 30.0

    def test_network_error_500_delay(self):
        """測試 HTTP 500 錯誤的延遲"""
        error = NetworkError("Server error", status_code=500)

        assert get_retry_delay(error) == 10.0

    def test_custom_base_delay(self):
        """測試自訂基礎延遲"""
        error = DownloadError("Error")

        assert get_retry_delay(error, base_delay=5.0) == 5.0


class TestCreateErrorContext:
    """測試 create_error_context 函數"""

    def test_basic_context(self):
        """測試基本上下文建立"""
        error = DownloadError("Test error")
        context = create_error_context(error)

        assert context['error_type'] == 'DownloadError'
        assert context['error_message'] == 'Test error'
        assert 'retryable' in context
        assert 'retry_delay' in context

    def test_context_with_file_id(self):
        """測試帶檔案 ID 的上下文"""
        error = DownloadError("Test error", file_id="abc123")
        context = create_error_context(error)

        assert context['file_id'] == 'abc123'

    def test_context_with_details(self):
        """測試帶詳細資訊的上下文"""
        error = DownloadError("Test error", details={"key": "value"})
        context = create_error_context(error)

        assert context['details'] == {"key": "value"}

    def test_network_error_context(self):
        """測試網路錯誤的上下文"""
        error = NetworkError("HTTP error", status_code=503)
        context = create_error_context(error)

        assert context['status_code'] == 503

    def test_validation_error_context(self):
        """測試驗證錯誤的上下文"""
        error = ValidationError("email", "invalid")
        context = create_error_context(error)

        assert context['field'] == 'email'
        assert context['value'] == 'invalid'

    def test_additional_context(self):
        """測試額外上下文資訊"""
        error = DownloadError("Test error")
        context = create_error_context(error, user="test_user", action="download")

        assert context['user'] == 'test_user'
        assert context['action'] == 'download'


if __name__ == '__main__':
    pytest.main([__file__])
