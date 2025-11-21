"""
統一錯誤處理模組測試
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import sys

sys.path.append(str(Path(__file__).parent.parent))

from src.utils.error_handler import (
    ErrorResult,
    ErrorHandler,
    ui_error_handler,
    handle_error,
    is_critical_error,
    should_retry,
    get_suggested_action
)
from src.utils.exceptions import (
    DownloadError,
    NetworkError,
    AuthenticationError,
    ConfigurationError,
    ValidationError,
    QuotaExceededError,
    FileNotFoundError,
    FilePermissionError,
    FatalError
)


class TestErrorResult:
    """測試錯誤結果類別"""

    def test_init_success(self):
        """測試成功結果初始化"""
        result = ErrorResult(success=True, data="test_data")

        assert result.success is True
        assert result.data == "test_data"
        assert result.error is None
        assert result.error_message is None
        assert result.error_code is None

    def test_init_failure(self):
        """測試失敗結果初始化"""
        error = ValueError("test error")
        result = ErrorResult(
            success=False,
            error=error,
            error_message="Test error occurred"
        )

        assert result.success is False
        assert result.error == error
        assert result.error_message == "Test error occurred"

    def test_bool_success(self):
        """測試布爾值 - 成功"""
        result = ErrorResult(success=True)
        assert bool(result) is True

    def test_bool_failure(self):
        """測試布爾值 - 失敗"""
        result = ErrorResult(success=False)
        assert bool(result) is False

    def test_ok_class_method(self):
        """測試 ok 類別方法"""
        result = ErrorResult.ok("success_data")

        assert result.success is True
        assert result.data == "success_data"
        assert result.error is None

    def test_fail_with_exception(self):
        """測試 fail 方法 - 異常物件"""
        error = ValueError("test error")
        result = ErrorResult.fail(error)

        assert result.success is False
        assert result.error == error
        assert result.error_message == "test error"
        assert result.error_code == "ValueError"

    def test_fail_with_string(self):
        """測試 fail 方法 - 字串"""
        result = ErrorResult.fail("Something went wrong")

        assert result.success is False
        assert result.error_message == "Something went wrong"
        assert result.error_code == "UnknownError"

    def test_fail_with_custom_error_code(self):
        """測試 fail 方法 - 自訂錯誤碼"""
        result = ErrorResult.fail("Error", error_code="CUSTOM_ERROR")

        assert result.error_code == "CUSTOM_ERROR"

    def test_to_dict(self):
        """測試轉換為字典"""
        result = ErrorResult.ok("test_data")
        result_dict = result.to_dict()

        assert result_dict['success'] is True
        assert result_dict['data'] == "test_data"
        assert result_dict['error_message'] is None
        assert result_dict['error_code'] is None


class TestErrorHandler:
    """測試錯誤處理器類別"""

    def test_get_user_friendly_message_known_error(self):
        """測試取得使用者友善訊息 - 已知錯誤"""
        error = NetworkError("Connection failed")
        message = ErrorHandler.get_user_friendly_message(error)

        assert "網路連接問題" in message

    def test_get_user_friendly_message_auth_error(self):
        """測試取得使用者友善訊息 - 認證錯誤"""
        error = AuthenticationError("Token expired")
        message = ErrorHandler.get_user_friendly_message(error)

        # 應該包含友善訊息，可能還有原始訊息
        assert "認證" in message or "登入" in message

    def test_get_user_friendly_message_unknown_error(self):
        """測試取得使用者友善訊息 - 未知錯誤"""
        error = Exception("Unknown error")
        message = ErrorHandler.get_user_friendly_message(error)

        assert "未預期" in message

    def test_get_user_friendly_message_download_error_with_file_id(self):
        """測試取得使用者友善訊息 - 帶檔案 ID"""
        error = DownloadError("Download failed", file_id="abc123")
        message = ErrorHandler.get_user_friendly_message(error)

        assert "abc123" in message

    def test_handle_api_error_decorator_success(self):
        """測試 API 錯誤處理裝飾器 - 成功"""
        @ErrorHandler.handle_api_error(reraise=True)
        def test_func():
            return "success"

        result = test_func()
        assert result == "success"

    def test_handle_api_error_decorator_network_error(self):
        """測試 API 錯誤處理裝飾器 - 網路錯誤"""
        @ErrorHandler.handle_api_error(reraise=True)
        def test_func():
            raise NetworkError("Network failure")

        with pytest.raises(DownloadError) as exc_info:
            test_func()

        assert "網路" in str(exc_info.value)

    def test_handle_api_error_decorator_no_reraise(self):
        """測試 API 錯誤處理裝飾器 - 不重新拋出"""
        @ErrorHandler.handle_api_error(reraise=False, default_return="default")
        def test_func():
            raise NetworkError("Network failure")

        result = test_func()
        assert result == "default"

    def test_handle_with_result_success(self):
        """測試結果包裝裝飾器 - 成功"""
        @ErrorHandler.handle_with_result
        def test_func():
            return "result_data"

        result = test_func()

        assert isinstance(result, ErrorResult)
        assert result.success is True
        assert result.data == "result_data"

    def test_handle_with_result_failure(self):
        """測試結果包裝裝飾器 - 失敗"""
        @ErrorHandler.handle_with_result
        def test_func():
            raise ValueError("Test error")

        result = test_func()

        assert isinstance(result, ErrorResult)
        assert result.success is False
        assert "Test error" in result.error_message

    def test_safe_execute_success(self):
        """測試安全執行 - 成功"""
        def test_func(a, b):
            return a + b

        result = ErrorHandler.safe_execute(test_func, 1, 2)
        assert result == 3

    def test_safe_execute_failure_with_default(self):
        """測試安全執行 - 失敗返回預設值"""
        def test_func():
            raise ValueError("Error")

        result = ErrorHandler.safe_execute(test_func, default="default_value")
        assert result == "default_value"

    def test_safe_execute_with_error_handler(self):
        """測試安全執行 - 自訂錯誤處理"""
        errors = []

        def error_handler(e):
            errors.append(str(e))

        def test_func():
            raise ValueError("Custom error")

        ErrorHandler.safe_execute(
            test_func,
            default=None,
            error_handler=error_handler
        )

        assert len(errors) == 1
        assert "Custom error" in errors[0]


class TestUIErrorHandler:
    """測試 UI 錯誤處理裝飾器"""

    @patch('src.utils.error_handler._show_ui_error')
    def test_ui_error_handler_success(self, mock_show_error):
        """測試 UI 錯誤處理 - 成功"""
        @ui_error_handler()
        def test_func():
            return "success"

        result = test_func()

        assert result == "success"
        mock_show_error.assert_not_called()

    @patch('src.utils.error_handler._show_ui_error')
    def test_ui_error_handler_auth_error(self, mock_show_error):
        """測試 UI 錯誤處理 - 認證錯誤"""
        @ui_error_handler()
        def test_func():
            raise AuthenticationError("Auth failed")

        result = test_func()

        assert result is None
        mock_show_error.assert_called_once()
        call_args = mock_show_error.call_args[0]
        assert "認證" in call_args[0]
        assert call_args[1] == "auth"

    @patch('src.utils.error_handler._show_ui_error')
    def test_ui_error_handler_download_error(self, mock_show_error):
        """測試 UI 錯誤處理 - 下載錯誤"""
        @ui_error_handler()
        def test_func():
            raise DownloadError("Download failed")

        result = test_func()

        assert result is None
        mock_show_error.assert_called_once()
        call_args = mock_show_error.call_args[0]
        assert call_args[1] == "download"

    @patch('src.utils.error_handler._show_ui_error')
    def test_ui_error_handler_unknown_error(self, mock_show_error):
        """測試 UI 錯誤處理 - 未知錯誤"""
        @ui_error_handler()
        def test_func():
            raise ValueError("Unknown")

        result = test_func()

        assert result is None
        mock_show_error.assert_called_once()
        call_args = mock_show_error.call_args[0]
        assert call_args[1] == "unknown"


class TestHandleError:
    """測試 handle_error 函數"""

    def test_handle_error_returns_result(self):
        """測試錯誤處理返回結果"""
        error = DownloadError("Test error")
        result = handle_error(error)

        assert isinstance(result, ErrorResult)
        assert result.success is False

    def test_handle_error_with_context(self):
        """測試帶上下文的錯誤處理"""
        error = DownloadError("Test error")
        result = handle_error(error, context="downloading file")

        assert result.success is False

    def test_handle_error_with_reraise(self):
        """測試重新拋出錯誤"""
        error = DownloadError("Test error")

        with pytest.raises(DownloadError):
            handle_error(error, reraise=True)


class TestIsCriticalError:
    """測試 is_critical_error 函數"""

    def test_auth_error_is_critical(self):
        """測試認證錯誤是嚴重錯誤"""
        error = AuthenticationError("Auth failed")
        assert is_critical_error(error) is True

    def test_config_error_is_critical(self):
        """測試配置錯誤是嚴重錯誤"""
        error = ConfigurationError("api_key")
        assert is_critical_error(error) is True

    def test_fatal_error_is_critical(self):
        """測試致命錯誤是嚴重錯誤"""
        error = FatalError("Fatal")
        assert is_critical_error(error) is True

    def test_network_error_not_critical(self):
        """測試網路錯誤不是嚴重錯誤"""
        error = NetworkError("Network failure")
        assert is_critical_error(error) is False

    def test_download_error_not_critical(self):
        """測試下載錯誤不是嚴重錯誤"""
        error = DownloadError("Download failed")
        assert is_critical_error(error) is False


class TestShouldRetry:
    """測試 should_retry 函數"""

    def test_network_error_should_retry(self):
        """測試網路錯誤應該重試"""
        error = NetworkError("Network failure")
        assert should_retry(error) is True

    def test_quota_exceeded_should_retry(self):
        """測試配額錯誤應該重試"""
        error = QuotaExceededError()
        assert should_retry(error) is True

    def test_auth_error_should_not_retry(self):
        """測試認證錯誤不應該重試"""
        error = AuthenticationError("Auth failed")
        assert should_retry(error) is False

    def test_fatal_error_should_not_retry(self):
        """測試致命錯誤不應該重試"""
        error = FatalError("Fatal")
        assert should_retry(error) is False


class TestGetSuggestedAction:
    """測試 get_suggested_action 函數"""

    def test_auth_error_suggestion(self):
        """測試認證錯誤的建議"""
        error = AuthenticationError("Auth failed")
        action = get_suggested_action(error)

        assert "登入" in action or "授權" in action

    def test_network_error_suggestion(self):
        """測試網路錯誤的建議"""
        error = NetworkError("Network failure")
        action = get_suggested_action(error)

        assert "網路" in action or "重試" in action

    def test_quota_exceeded_suggestion(self):
        """測試配額錯誤的建議"""
        error = QuotaExceededError()
        action = get_suggested_action(error)

        assert "等待" in action or "重試" in action

    def test_file_not_found_suggestion(self):
        """測試檔案不存在的建議"""
        error = FileNotFoundError("abc123")
        action = get_suggested_action(error)

        assert "檔案" in action or "ID" in action or "URL" in action

    def test_file_permission_suggestion(self):
        """測試權限錯誤的建議"""
        error = FilePermissionError("abc123")
        action = get_suggested_action(error)

        assert "權限" in action

    def test_config_error_suggestion(self):
        """測試配置錯誤的建議"""
        error = ConfigurationError("api_key")
        action = get_suggested_action(error)

        assert "配置" in action

    def test_validation_error_suggestion(self):
        """測試驗證錯誤的建議"""
        error = ValidationError("email", "invalid")
        action = get_suggested_action(error)

        assert "輸入" in action or "資料" in action or "格式" in action

    def test_unknown_error_suggestion(self):
        """測試未知錯誤的建議"""
        error = Exception("Unknown")
        action = get_suggested_action(error)

        assert "重試" in action or "支援" in action


if __name__ == '__main__':
    pytest.main([__file__])
