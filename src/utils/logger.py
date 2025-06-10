"""
日誌管理模組
提供結構化日誌功能
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
from .config import get_config


class ColoredFormatter(logging.Formatter):
    """彩色日誌格式器"""
    
    # ANSI 顏色代碼
    COLORS = {
        'DEBUG': '\033[36m',    # 青色
        'INFO': '\033[32m',     # 綠色
        'WARNING': '\033[33m',  # 黃色
        'ERROR': '\033[31m',    # 紅色
        'CRITICAL': '\033[35m', # 紫色
        'RESET': '\033[0m'      # 重設
    }
    
    def format(self, record):
        # 添加顏色
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
        
        return super().format(record)


def setup_logger(name: str = None, level: Optional[str] = None) -> logging.Logger:
    """設定日誌器
    
    Args:
        name: 日誌器名稱，None 則使用根日誌器
        level: 日誌等級，None 則從配置讀取
        
    Returns:
        配置好的日誌器
    """
    logger = logging.getLogger(name)
    
    # 避免重複設定
    if logger.handlers:
        return logger
    
    # 從配置讀取設定
    log_level = level or get_config('logging.level', 'INFO')
    log_file = get_config('logging.file', 'logs/app.log')
    log_format = get_config(
        'logging.format', 
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    max_size = get_config('logging.max_size', 10485760)  # 10MB
    backup_count = get_config('logging.backup_count', 5)
    
    # 設定日誌等級
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # 建立格式器
    formatter = logging.Formatter(log_format, '%Y-%m-%d %H:%M:%S')
    
    # 建立控制台處理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # 如果是開發環境，使用彩色格式器
    if get_config('web.debug', False):
        colored_formatter = ColoredFormatter(log_format, '%Y-%m-%d %H:%M:%S')
        console_handler.setFormatter(colored_formatter)
    else:
        console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    # 建立檔案處理器
    if log_file:
        try:
            # 確保日誌目錄存在
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 使用 RotatingFileHandler 進行日誌輪轉
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(getattr(logging, log_level.upper()))
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
        except Exception as e:
            logger.error(f"無法建立檔案日誌處理器: {e}")
    
    # 避免日誌訊息向上傳播（防止重複輸出）
    logger.propagate = False
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """取得日誌器
    
    Args:
        name: 日誌器名稱
        
    Returns:
        日誌器實例
    """
    if name is None:
        name = __name__.split('.')[0]  # 使用套件名稱
    
    logger = logging.getLogger(name)
    
    # 如果日誌器尚未設定，進行設定
    if not logger.handlers:
        setup_logger(name)
    
    return logger


class LoggerMixin:
    """日誌器混入類別
    
    為類別提供日誌功能
    """
    
    @property
    def logger(self) -> logging.Logger:
        """取得類別專用的日誌器"""
        if not hasattr(self, '_logger'):
            self._logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        return self._logger


# 建立主要日誌器
main_logger = setup_logger('gdrive_downloader')

# 為了向後相容性，提供別名
setup_logging = setup_logger


def log_function_call(func):
    """裝飾器：記錄函數呼叫
    
    Args:
        func: 要裝飾的函數
        
    Returns:
        裝飾後的函數
    """
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.debug(f"呼叫函數: {func.__name__}")
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"函數 {func.__name__} 執行成功")
            return result
        except Exception as e:
            logger.error(f"函數 {func.__name__} 執行失敗: {e}")
            raise
    
    return wrapper


async def log_async_function_call(func):
    """裝飾器：記錄異步函數呼叫
    
    Args:
        func: 要裝飾的異步函數
        
    Returns:
        裝飾後的異步函數
    """
    async def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.debug(f"呼叫異步函數: {func.__name__}")
        
        try:
            result = await func(*args, **kwargs)
            logger.debug(f"異步函數 {func.__name__} 執行成功")
            return result
        except Exception as e:
            logger.error(f"異步函數 {func.__name__} 執行失敗: {e}")
            raise
    
    return wrapper 