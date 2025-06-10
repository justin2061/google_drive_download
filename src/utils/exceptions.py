"""
自定義例外類別
提供系統特定的例外處理
"""

from typing import Optional


class DownloadError(Exception):
    """下載相關例外基類"""
    
    def __init__(self, message: str, error_type: str = None, file_id: str = None, details: dict = None):
        super().__init__(message)
        self.error_type = error_type or self.__class__.__name__
        self.file_id = file_id
        self.details = details or {}
        
    def __str__(self):
        base_msg = super().__str__()
        if self.file_id:
            return f"{base_msg} (檔案ID: {self.file_id})"
        return base_msg


class NetworkError(DownloadError):
    """網路相關例外"""
    
    def __init__(self, message: str, status_code: int = None, **kwargs):
        super().__init__(message, **kwargs)
        self.status_code = status_code


class AuthenticationError(DownloadError):
    """認證相關例外"""
    pass


class QuotaExceededError(DownloadError):
    """配額超限例外"""
    
    def __init__(self, message: str = "Google Drive API 配額已超限", **kwargs):
        super().__init__(message, **kwargs)


class FileNotFoundError(DownloadError):
    """檔案不存在例外"""
    
    def __init__(self, file_id: str, message: str = None, **kwargs):
        message = message or f"找不到檔案"
        super().__init__(message, file_id=file_id, **kwargs)


class FilePermissionError(DownloadError):
    """檔案權限例外"""
    
    def __init__(self, file_id: str, message: str = None, **kwargs):
        message = message or f"沒有檔案存取權限"
        super().__init__(message, file_id=file_id, **kwargs)


class ConfigurationError(DownloadError):
    """配置錯誤例外"""
    
    def __init__(self, config_key: str, message: str = None, **kwargs):
        message = message or f"配置錯誤: {config_key}"
        super().__init__(message, **kwargs)
        self.config_key = config_key


class ValidationError(DownloadError):
    """驗證錯誤例外"""
    
    def __init__(self, field: str, value: any, message: str = None, **kwargs):
        message = message or f"驗證失敗: {field} = {value}"
        super().__init__(message, **kwargs)
        self.field = field
        self.value = value


class RetryableError(DownloadError):
    """可重試的例外"""
    
    def __init__(self, message: str, retry_after: float = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after  # 建議重試間隔（秒）


class FatalError(DownloadError):
    """致命錯誤例外（不可重試）"""
    pass


# 例外處理工具函數
def is_retryable_error(error: Exception) -> bool:
    """判斷例外是否可重試
    
    Args:
        error: 例外實例
        
    Returns:
        True if retryable, False otherwise
    """
    if isinstance(error, FatalError):
        return False
    
    if isinstance(error, RetryableError):
        return True
    
    if isinstance(error, (NetworkError, QuotaExceededError)):
        return True
    
    if isinstance(error, AuthenticationError):
        return False
    
    # 對於其他例外，預設為可重試
    return True


def get_retry_delay(error: Exception, base_delay: float = 1.0) -> float:
    """取得重試延遲時間
    
    Args:
        error: 例外實例
        base_delay: 基礎延遲時間
        
    Returns:
        建議的延遲時間（秒）
    """
    if isinstance(error, RetryableError) and error.retry_after:
        return error.retry_after
    
    if isinstance(error, QuotaExceededError):
        return 60.0  # 配額錯誤建議等待1分鐘
    
    if isinstance(error, NetworkError):
        if hasattr(error, 'status_code'):
            if error.status_code == 429:  # Too Many Requests
                return 30.0
            elif error.status_code >= 500:  # Server Error
                return 10.0
    
    return base_delay


def create_error_context(error: Exception, **additional_context) -> dict:
    """建立錯誤上下文資訊
    
    Args:
        error: 例外實例
        **additional_context: 額外的上下文資訊
        
    Returns:
        錯誤上下文字典
    """
    context = {
        'error_type': type(error).__name__,
        'error_message': str(error),
        'retryable': is_retryable_error(error),
        'retry_delay': get_retry_delay(error)
    }
    
    # 添加例外特有的屬性
    if isinstance(error, DownloadError):
        if error.file_id:
            context['file_id'] = error.file_id
        if error.details:
            context['details'] = error.details
    
    if isinstance(error, NetworkError) and hasattr(error, 'status_code'):
        context['status_code'] = error.status_code
    
    if isinstance(error, ValidationError):
        context['field'] = error.field
        context['value'] = error.value
    
    # 添加額外的上下文資訊
    context.update(additional_context)
    
    return context 