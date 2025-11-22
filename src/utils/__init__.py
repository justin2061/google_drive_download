"""
工具與輔助功能模組
"""

from .config import ConfigManager
from .logger import setup_logger, get_logger
from .helpers import slugify, format_size, format_time
from .exceptions import *
from .error_handler import (
    ErrorHandler,
    ErrorResult,
    ui_error_handler,
    handle_error,
    is_critical_error,
    should_retry,
    get_suggested_action
)

__all__ = [
    'ConfigManager',
    'setup_logger',
    'get_logger',
    'slugify',
    'format_size',
    'format_time',
    'DownloadError',
    'NetworkError',
    'AuthenticationError',
    'QuotaExceededError',
    # 錯誤處理
    'ErrorHandler',
    'ErrorResult',
    'ui_error_handler',
    'handle_error',
    'is_critical_error',
    'should_retry',
    'get_suggested_action'
] 