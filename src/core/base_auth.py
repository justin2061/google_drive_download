"""
基礎認證抽象類別
定義所有認證方式的統一介面
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from ..utils.logger import LoggerMixin


class BaseAuth(LoggerMixin, ABC):
    """基礎認證抽象類別
    
    所有認證提供者的基底類別，定義統一的認證介面
    """
    
    def __init__(self, scopes: list = None):
        """
        初始化基礎認證
        
        Args:
            scopes: 權限範圍清單
        """
        self.scopes = scopes or ['https://www.googleapis.com/auth/drive.readonly']
        self._credentials = None
        self._drive_service = None
        self._authenticated = False
    
    @abstractmethod
    def authenticate(self, force_refresh: bool = False) -> bool:
        """執行認證
        
        Args:
            force_refresh: 強制重新認證
            
        Returns:
            認證是否成功
        """
        pass
    
    @abstractmethod
    def get_drive_service(self):
        """取得 Google Drive 服務實例
        
        Returns:
            Google Drive 服務實例
        """
        pass
    
    def is_authenticated(self) -> bool:
        """檢查是否已認證
        
        Returns:
            是否已認證
        """
        return self._authenticated and self._credentials is not None
    
    def get_credentials(self):
        """取得認證憑證
        
        Returns:
            認證憑證
        """
        return self._credentials
    
    def get_auth_info(self) -> Dict[str, Any]:
        """取得認證資訊
        
        Returns:
            認證相關資訊
        """
        return {
            'type': self.__class__.__name__,
            'authenticated': self.is_authenticated(),
            'scopes': self.scopes,
            'credentials_available': self._credentials is not None
        }
    
    def logout(self):
        """登出並清理認證資料"""
        self._credentials = None
        self._drive_service = None
        self._authenticated = False
        self.logger.info("已登出")


class AuthResult:
    """認證結果類別"""
    
    def __init__(self, success: bool, message: str = "", error: Exception = None, 
                 auth_type: str = "", user_info: Dict[str, Any] = None):
        self.success = success
        self.message = message
        self.error = error
        self.auth_type = auth_type
        self.user_info = user_info or {}
    
    def __bool__(self):
        return self.success
    
    def __str__(self):
        status = "成功" if self.success else "失敗"
        return f"認證{status}: {self.message}" 