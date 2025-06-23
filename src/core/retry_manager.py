"""
重試管理器
提供智慧的錯誤處理和重試機制
"""

import asyncio
import time
import random
from typing import Callable, Any, Dict, List, Optional, Tuple, Union
from enum import Enum
from functools import wraps
from datetime import datetime, timedelta

from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError, TransportError
import requests.exceptions

from ..utils.logger import LoggerMixin
from ..utils.exceptions import AuthenticationError, ConfigurationError


class RetryStrategy(Enum):
    """重試策略"""
    FIXED = "fixed"           # 固定間隔
    EXPONENTIAL = "exponential"  # 指數退避
    LINEAR = "linear"         # 線性增長
    RANDOM = "random"         # 隨機間隔


class ErrorCategory(Enum):
    """錯誤分類"""
    NETWORK = "network"           # 網路錯誤
    AUTH = "auth"                # 認證錯誤
    RATE_LIMIT = "rate_limit"    # 速率限制
    SERVER = "server"            # 伺服器錯誤
    CLIENT = "client"            # 客戶端錯誤
    UNKNOWN = "unknown"          # 未知錯誤


class RetryResult:
    """重試結果"""
    
    def __init__(self, success: bool, result: Any = None, error: Exception = None, 
                 attempts: int = 0, total_time: float = 0.0):
        self.success = success
        self.result = result
        self.error = error
        self.attempts = attempts
        self.total_time = total_time
    
    def __bool__(self):
        return self.success


class RetryManager(LoggerMixin):
    """智慧重試管理器
    
    提供多種重試策略和錯誤分類處理
    """
    
    # 可重試的錯誤類型
    RETRYABLE_HTTP_CODES = {
        429,  # Too Many Requests
        500,  # Internal Server Error
        502,  # Bad Gateway
        503,  # Service Unavailable
        504,  # Gateway Timeout
    }
    
    RETRYABLE_EXCEPTIONS = (
        ConnectionError,
        TimeoutError,
        requests.exceptions.RequestException,
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        TransportError,
    )
    
    def __init__(self, 
                 max_retries: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
                 jitter: bool = True,
                 backoff_factor: float = 2.0):
        """
        初始化重試管理器
        
        Args:
            max_retries: 最大重試次數
            base_delay: 基礎延遲時間（秒）
            max_delay: 最大延遲時間（秒）
            strategy: 重試策略
            jitter: 是否添加隨機抖動
            backoff_factor: 退避因子
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.strategy = strategy
        self.jitter = jitter
        self.backoff_factor = backoff_factor
        
        # 統計資訊
        self._stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'total_retries': 0,
            'error_counts': {}
        }
        
        self.logger.info(f"重試管理器已初始化 - 策略: {strategy.value}, 最大重試: {max_retries}")
    
    def classify_error(self, error: Exception) -> ErrorCategory:
        """分類錯誤類型
        
        Args:
            error: 異常物件
            
        Returns:
            錯誤分類
        """
        if isinstance(error, HttpError):
            status_code = error.resp.status
            
            if status_code == 429:
                return ErrorCategory.RATE_LIMIT
            elif 400 <= status_code < 500:
                if status_code in [401, 403]:
                    return ErrorCategory.AUTH
                else:
                    return ErrorCategory.CLIENT
            elif 500 <= status_code < 600:
                return ErrorCategory.SERVER
        
        elif isinstance(error, (RefreshError, AuthenticationError)):
            return ErrorCategory.AUTH
        
        elif isinstance(error, self.RETRYABLE_EXCEPTIONS):
            return ErrorCategory.NETWORK
        
        return ErrorCategory.UNKNOWN
    
    def is_retryable(self, error: Exception) -> bool:
        """判斷錯誤是否可重試
        
        Args:
            error: 異常物件
            
        Returns:
            是否可重試
        """
        error_category = self.classify_error(error)
        
        # 根據錯誤分類判斷是否可重試
        if error_category in [ErrorCategory.NETWORK, ErrorCategory.RATE_LIMIT, ErrorCategory.SERVER]:
            return True
        
        # HTTP 錯誤特殊處理
        if isinstance(error, HttpError):
            return error.resp.status in self.RETRYABLE_HTTP_CODES
        
        # 其他可重試的異常
        if isinstance(error, self.RETRYABLE_EXCEPTIONS):
            return True
        
        return False
    
    def calculate_delay(self, attempt: int, error: Exception = None) -> float:
        """計算延遲時間
        
        Args:
            attempt: 重試次數
            error: 異常物件（用於特殊處理）
            
        Returns:
            延遲時間（秒）
        """
        if self.strategy == RetryStrategy.FIXED:
            delay = self.base_delay
        
        elif self.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.base_delay * (self.backoff_factor ** attempt)
        
        elif self.strategy == RetryStrategy.LINEAR:
            delay = self.base_delay + (attempt * self.base_delay)
        
        elif self.strategy == RetryStrategy.RANDOM:
            delay = random.uniform(self.base_delay, self.base_delay * 3)
        
        else:
            delay = self.base_delay
        
        # 特殊錯誤的延遲調整
        if error and isinstance(error, HttpError):
            if error.resp.status == 429:  # Rate limit
                # 檢查 Retry-After 標頭
                retry_after = error.resp.get('retry-after')
                if retry_after:
                    try:
                        suggested_delay = float(retry_after)
                        delay = max(delay, suggested_delay)
                    except (ValueError, TypeError):
                        pass
        
        # 限制最大延遲
        delay = min(delay, self.max_delay)
        
        # 添加隨機抖動
        if self.jitter:
            jitter_range = delay * 0.1  # 10% 抖動
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)
    
    def retry_sync(self, 
                   func: Callable, 
                   *args, 
                   max_retries: int = None,
                   custom_exceptions: Tuple = None,
                   **kwargs) -> RetryResult:
        """同步重試執行
        
        Args:
            func: 要執行的函數
            *args: 函數參數
            max_retries: 自訂最大重試次數
            custom_exceptions: 自訂可重試的異常類型
            **kwargs: 函數關鍵字參數
            
        Returns:
            重試結果
        """
        max_retries = max_retries if max_retries is not None else self.max_retries
        start_time = time.time()
        attempt = 0
        last_error = None
        
        self._stats['total_calls'] += 1
        
        while attempt <= max_retries:
            try:
                self.logger.debug(f"執行嘗試 {attempt + 1}/{max_retries + 1}: {func.__name__}")
                
                result = func(*args, **kwargs)
                
                total_time = time.time() - start_time
                
                if attempt > 0:
                    self.logger.info(f"重試成功 - 函數: {func.__name__}, 嘗試次數: {attempt + 1}, 總時間: {total_time:.2f}s")
                    self._stats['total_retries'] += attempt
                
                self._stats['successful_calls'] += 1
                
                return RetryResult(
                    success=True,
                    result=result,
                    attempts=attempt + 1,
                    total_time=total_time
                )
                
            except Exception as e:
                last_error = e
                attempt += 1
                
                # 記錄錯誤統計
                error_type = type(e).__name__
                self._stats['error_counts'][error_type] = self._stats['error_counts'].get(error_type, 0) + 1
                
                # 判斷是否應該重試
                should_retry = False
                
                if custom_exceptions and isinstance(e, custom_exceptions):
                    should_retry = True
                elif self.is_retryable(e):
                    should_retry = True
                
                if not should_retry or attempt > max_retries:
                    self.logger.error(f"函數執行失敗 - {func.__name__}: {e}")
                    break
                
                # 計算延遲時間並等待
                delay = self.calculate_delay(attempt - 1, e)
                error_category = self.classify_error(e)
                
                self.logger.warning(
                    f"重試 {attempt}/{max_retries} - 函數: {func.__name__}, "
                    f"錯誤: {error_category.value}, 延遲: {delay:.2f}s"
                )
                
                if delay > 0:
                    time.sleep(delay)
        
        # 所有重試都失敗
        total_time = time.time() - start_time
        self._stats['failed_calls'] += 1
        self._stats['total_retries'] += max_retries
        
        self.logger.error(f"重試失敗 - 函數: {func.__name__}, 總嘗試: {attempt}, 總時間: {total_time:.2f}s")
        
        return RetryResult(
            success=False,
            error=last_error,
            attempts=attempt,
            total_time=total_time
        )
    
    async def retry_async(self, 
                          func: Callable, 
                          *args, 
                          max_retries: int = None,
                          custom_exceptions: Tuple = None,
                          **kwargs) -> RetryResult:
        """異步重試執行
        
        Args:
            func: 要執行的異步函數
            *args: 函數參數
            max_retries: 自訂最大重試次數
            custom_exceptions: 自訂可重試的異常類型
            **kwargs: 函數關鍵字參數
            
        Returns:
            重試結果
        """
        max_retries = max_retries if max_retries is not None else self.max_retries
        start_time = time.time()
        attempt = 0
        last_error = None
        
        self._stats['total_calls'] += 1
        
        while attempt <= max_retries:
            try:
                self.logger.debug(f"異步執行嘗試 {attempt + 1}/{max_retries + 1}: {func.__name__}")
                
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                total_time = time.time() - start_time
                
                if attempt > 0:
                    self.logger.info(f"異步重試成功 - 函數: {func.__name__}, 嘗試次數: {attempt + 1}, 總時間: {total_time:.2f}s")
                    self._stats['total_retries'] += attempt
                
                self._stats['successful_calls'] += 1
                
                return RetryResult(
                    success=True,
                    result=result,
                    attempts=attempt + 1,
                    total_time=total_time
                )
                
            except Exception as e:
                last_error = e
                attempt += 1
                
                # 記錄錯誤統計
                error_type = type(e).__name__
                self._stats['error_counts'][error_type] = self._stats['error_counts'].get(error_type, 0) + 1
                
                # 判斷是否應該重試
                should_retry = False
                
                if custom_exceptions and isinstance(e, custom_exceptions):
                    should_retry = True
                elif self.is_retryable(e):
                    should_retry = True
                
                if not should_retry or attempt > max_retries:
                    self.logger.error(f"異步函數執行失敗 - {func.__name__}: {e}")
                    break
                
                # 計算延遲時間並等待
                delay = self.calculate_delay(attempt - 1, e)
                error_category = self.classify_error(e)
                
                self.logger.warning(
                    f"異步重試 {attempt}/{max_retries} - 函數: {func.__name__}, "
                    f"錯誤: {error_category.value}, 延遲: {delay:.2f}s"
                )
                
                if delay > 0:
                    await asyncio.sleep(delay)
        
        # 所有重試都失敗
        total_time = time.time() - start_time
        self._stats['failed_calls'] += 1
        self._stats['total_retries'] += max_retries
        
        self.logger.error(f"異步重試失敗 - 函數: {func.__name__}, 總嘗試: {attempt}, 總時間: {total_time:.2f}s")
        
        return RetryResult(
            success=False,
            error=last_error,
            attempts=attempt,
            total_time=total_time
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """取得統計資訊
        
        Returns:
            統計資訊字典
        """
        total_calls = self._stats['total_calls']
        success_rate = (self._stats['successful_calls'] / total_calls * 100) if total_calls > 0 else 0
        
        return {
            'total_calls': total_calls,
            'successful_calls': self._stats['successful_calls'],
            'failed_calls': self._stats['failed_calls'],
            'success_rate': f"{success_rate:.2f}%",
            'total_retries': self._stats['total_retries'],
            'average_retries': self._stats['total_retries'] / total_calls if total_calls > 0 else 0,
            'error_counts': self._stats['error_counts'].copy(),
            'config': {
                'max_retries': self.max_retries,
                'base_delay': self.base_delay,
                'max_delay': self.max_delay,
                'strategy': self.strategy.value,
                'jitter': self.jitter
            }
        }
    
    def reset_stats(self):
        """重置統計資訊"""
        self._stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'total_retries': 0,
            'error_counts': {}
        }
        self.logger.info("重試統計已重置")


def retry(max_retries: int = 3,
          base_delay: float = 1.0,
          max_delay: float = 60.0,
          strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
          custom_exceptions: Tuple = None):
    """重試裝飾器
    
    Args:
        max_retries: 最大重試次數
        base_delay: 基礎延遲時間
        max_delay: 最大延遲時間
        strategy: 重試策略
        custom_exceptions: 自訂可重試的異常類型
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retry_manager = RetryManager(
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                strategy=strategy
            )
            
            result = retry_manager.retry_sync(
                func, *args, 
                custom_exceptions=custom_exceptions,
                **kwargs
            )
            
            if result.success:
                return result.result
            else:
                raise result.error
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            retry_manager = RetryManager(
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                strategy=strategy
            )
            
            result = await retry_manager.retry_async(
                func, *args,
                custom_exceptions=custom_exceptions,
                **kwargs
            )
            
            if result.success:
                return result.result
            else:
                raise result.error
        
        # 根據函數類型返回適當的包裝器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return wrapper
    
    return decorator


# 全域重試管理器實例
default_retry_manager = RetryManager()


def quick_retry(func: Callable, *args, **kwargs) -> Any:
    """快速重試函數
    
    Args:
        func: 要執行的函數
        *args: 函數參數
        **kwargs: 函數關鍵字參數
        
    Returns:
        函數執行結果
        
    Raises:
        Exception: 重試失敗後的最後一個異常
    """
    result = default_retry_manager.retry_sync(func, *args, **kwargs)
    
    if result.success:
        return result.result
    else:
        raise result.error 