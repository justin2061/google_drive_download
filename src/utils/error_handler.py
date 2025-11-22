"""
統一錯誤處理模組
提供一致的錯誤處理機制和裝飾器
"""

from typing import Callable, Any, Optional, TypeVar, Union
from functools import wraps
import traceback

from .logger import get_logger
from .exceptions import (
    DownloadError,
    NetworkError,
    AuthenticationError,
    FileNotFoundError,
    FilePermissionError,
    ConfigurationError,
    ValidationError,
    QuotaExceededError,
    RetryableError,
    FatalError,
    is_retryable_error,
    get_retry_delay,
    create_error_context
)

logger = get_logger(__name__)

# 類型變數用於泛型返回
T = TypeVar('T')


class ErrorResult:
    """錯誤結果類別

    用於包裝操作結果，區分成功和失敗
    """

    def __init__(
        self,
        success: bool,
        data: Any = None,
        error: Optional[Exception] = None,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None
    ):
        self.success = success
        self.data = data
        self.error = error
        self.error_message = error_message or (str(error) if error else None)
        self.error_code = error_code or (type(error).__name__ if error else None)

    def __bool__(self):
        return self.success

    @classmethod
    def ok(cls, data: Any = None) -> 'ErrorResult':
        """建立成功結果"""
        return cls(success=True, data=data)

    @classmethod
    def fail(
        cls,
        error: Union[Exception, str],
        error_code: Optional[str] = None
    ) -> 'ErrorResult':
        """建立失敗結果"""
        if isinstance(error, Exception):
            return cls(
                success=False,
                error=error,
                error_message=str(error),
                error_code=error_code or type(error).__name__
            )
        else:
            return cls(
                success=False,
                error_message=str(error),
                error_code=error_code or "UnknownError"
            )

    def to_dict(self) -> dict:
        """轉換為字典"""
        return {
            'success': self.success,
            'data': self.data,
            'error_message': self.error_message,
            'error_code': self.error_code
        }


class ErrorHandler:
    """統一錯誤處理器

    提供裝飾器和工具方法用於統一的錯誤處理
    """

    # 錯誤訊息映射
    ERROR_MESSAGES = {
        'FileNotFoundError': '找不到指定的檔案或資料夾',
        'FilePermissionError': '沒有存取權限',
        'NetworkError': '網路連接問題',
        'AuthenticationError': '認證失敗，請重新登入',
        'ConfigurationError': '配置錯誤',
        'ValidationError': '輸入驗證失敗',
        'QuotaExceededError': 'API 配額已超限，請稍後再試',
        'TimeoutError': '操作超時，請重試',
        'ConnectionError': '無法連接到伺服器',
    }

    @classmethod
    def get_user_friendly_message(cls, error: Exception) -> str:
        """取得使用者友善的錯誤訊息"""
        error_type = type(error).__name__

        # 使用映射表
        if error_type in cls.ERROR_MESSAGES:
            base_message = cls.ERROR_MESSAGES[error_type]
        else:
            base_message = "發生未預期的錯誤"

        # 添加詳細資訊
        if isinstance(error, DownloadError):
            if error.file_id:
                return f"{base_message} (檔案ID: {error.file_id})"

        return f"{base_message}: {str(error)}"

    @staticmethod
    def handle_api_error(
        reraise: bool = True,
        default_return: Any = None,
        log_level: str = "error"
    ):
        """API 錯誤處理裝飾器

        Args:
            reraise: 是否重新拋出異常
            default_return: 發生錯誤時的預設返回值
            log_level: 日誌等級 (debug, info, warning, error)

        Returns:
            裝飾器函數
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)

                except FileNotFoundError as e:
                    _log_error(log_level, f"檔案不存在: {e}")
                    if reraise:
                        raise DownloadError(
                            f"找不到指定的檔案或資料夾",
                            file_id=e.file_id if hasattr(e, 'file_id') else None
                        )
                    return default_return

                except FilePermissionError as e:
                    _log_error(log_level, f"權限錯誤: {e}")
                    if reraise:
                        raise DownloadError(
                            f"沒有存取權限",
                            file_id=e.file_id if hasattr(e, 'file_id') else None
                        )
                    return default_return

                except NetworkError as e:
                    _log_error(log_level, f"網路錯誤: {e}")
                    if reraise:
                        raise DownloadError(f"網路連接問題: {e}")
                    return default_return

                except AuthenticationError as e:
                    _log_error(log_level, f"認證錯誤: {e}")
                    if reraise:
                        raise
                    return default_return

                except QuotaExceededError as e:
                    _log_error(log_level, f"配額超限: {e}")
                    if reraise:
                        raise
                    return default_return

                except ValidationError as e:
                    _log_error(log_level, f"驗證錯誤: {e}")
                    if reraise:
                        raise
                    return default_return

                except Exception as e:
                    _log_error("error", f"未預期的錯誤: {e}\n{traceback.format_exc()}")
                    if reraise:
                        raise DownloadError(f"發生未預期的錯誤: {str(e)}")
                    return default_return

            return wrapper
        return decorator

    @staticmethod
    def handle_with_result(func: Callable[..., T]) -> Callable[..., ErrorResult]:
        """將函數包裝為返回 ErrorResult 的形式

        Args:
            func: 要包裝的函數

        Returns:
            返回 ErrorResult 的函數
        """
        @wraps(func)
        def wrapper(*args, **kwargs) -> ErrorResult:
            try:
                result = func(*args, **kwargs)
                return ErrorResult.ok(result)
            except Exception as e:
                logger.error(f"函數 {func.__name__} 執行失敗: {e}")
                return ErrorResult.fail(e)

        return wrapper

    @staticmethod
    def safe_execute(
        func: Callable[..., T],
        *args,
        default: T = None,
        error_handler: Callable[[Exception], None] = None,
        **kwargs
    ) -> T:
        """安全執行函數

        Args:
            func: 要執行的函數
            *args: 函數參數
            default: 預設返回值
            error_handler: 自訂錯誤處理函數
            **kwargs: 函數關鍵字參數

        Returns:
            函數結果或預設值
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"安全執行失敗 - {func.__name__}: {e}")
            if error_handler:
                error_handler(e)
            return default


def _log_error(level: str, message: str):
    """根據等級記錄錯誤"""
    log_func = getattr(logger, level, logger.error)
    log_func(message)


# Streamlit 專用錯誤處理
def ui_error_handler(show_traceback: bool = False):
    """Streamlit UI 錯誤處理裝飾器

    Args:
        show_traceback: 是否顯示堆疊追蹤

    Returns:
        裝飾器函數
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except AuthenticationError as e:
                _show_ui_error(f"認證失敗: {e}", "auth")
                return None
            except DownloadError as e:
                _show_ui_error(str(e), "download")
                return None
            except Exception as e:
                error_msg = f"發生未預期的錯誤: {str(e)}"
                if show_traceback:
                    error_msg += f"\n\n```\n{traceback.format_exc()}\n```"
                _show_ui_error(error_msg, "unknown")
                logger.exception(f"UI 未預期錯誤: {e}")
                return None

        return wrapper
    return decorator


def _show_ui_error(message: str, error_type: str):
    """顯示 UI 錯誤訊息"""
    try:
        import streamlit as st

        # 根據錯誤類型選擇圖示
        icons = {
            'auth': '🔐',
            'download': '📥',
            'network': '🌐',
            'unknown': '❌'
        }
        icon = icons.get(error_type, '❌')

        st.error(f"{icon} {message}")

    except ImportError:
        # 如果不在 Streamlit 環境中，僅記錄日誌
        logger.error(f"UI 錯誤: {message}")


# 便利函數
def handle_error(
    error: Exception,
    context: str = None,
    reraise: bool = False
) -> ErrorResult:
    """處理錯誤並返回結果

    Args:
        error: 異常物件
        context: 錯誤上下文描述
        reraise: 是否重新拋出異常

    Returns:
        ErrorResult 物件
    """
    error_context = create_error_context(error, context=context)
    user_message = ErrorHandler.get_user_friendly_message(error)

    logger.error(
        f"錯誤處理 - {context or 'Unknown'}: {user_message}",
        extra=error_context
    )

    if reraise:
        raise error

    return ErrorResult.fail(error)


def is_critical_error(error: Exception) -> bool:
    """判斷是否為嚴重錯誤

    Args:
        error: 異常物件

    Returns:
        是否為嚴重錯誤
    """
    critical_types = (
        AuthenticationError,
        ConfigurationError,
        FatalError
    )
    return isinstance(error, critical_types)


def should_retry(error: Exception) -> bool:
    """判斷是否應該重試

    Args:
        error: 異常物件

    Returns:
        是否應該重試
    """
    return is_retryable_error(error) and not is_critical_error(error)


def get_suggested_action(error: Exception) -> str:
    """取得建議的操作

    Args:
        error: 異常物件

    Returns:
        建議操作描述
    """
    if isinstance(error, AuthenticationError):
        return "請重新登入並授權"
    elif isinstance(error, NetworkError):
        return "請檢查網路連接後重試"
    elif isinstance(error, QuotaExceededError):
        return "請等待幾分鐘後重試，或使用其他認證方式"
    elif isinstance(error, FileNotFoundError):
        return "請確認檔案 ID 或 URL 是否正確"
    elif isinstance(error, FilePermissionError):
        return "請確認您有權限存取此檔案"
    elif isinstance(error, ConfigurationError):
        return "請檢查配置檔案設定"
    elif isinstance(error, ValidationError):
        return "請檢查輸入的資料格式"
    else:
        return "請稍後重試，如問題持續請聯繫支援"
