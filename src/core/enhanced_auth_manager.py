"""
增強的認證管理器
整合工廠模式、安全儲存和重試機制
"""

from typing import Optional, Dict, Any, List
from datetime import datetime

from .auth_factory import AuthFactory, AuthStrategyManager, AuthType, AuthResult
from .secure_token_storage import SecureTokenStorage
from .retry_manager import RetryManager, retry
from .base_auth import BaseAuth
from ..utils.logger import LoggerMixin
from ..utils.exceptions import AuthenticationError
from ..utils.config import get_config


class EnhancedAuthManager(LoggerMixin):
    """增強的認證管理器
    
    提供以下功能：
    - 統一認證工廠
    - 安全令牌儲存
    - 智慧重試機制
    - 多使用者支援
    - 認證狀態監控
    """
    
    def __init__(self, 
                 preferred_auth_types: List[str] = None,
                 enable_secure_storage: bool = True,
                 enable_retry: bool = True):
        """
        初始化增強認證管理器
        
        Args:
            preferred_auth_types: 偏好的認證類型順序
            enable_secure_storage: 是否啟用安全儲存
            enable_retry: 是否啟用重試機制
        """
        self.preferred_auth_types = preferred_auth_types or [
            AuthType.ADC.value,
            AuthType.OAUTH.value,
            AuthType.SERVICE_ACCOUNT.value
        ]
        
        # 初始化子系統
        self.auth_factory = AuthFactory()
        self.strategy_manager = AuthStrategyManager(self.preferred_auth_types)
        
        # 安全儲存
        self.secure_storage = None
        if enable_secure_storage:
            try:
                self.secure_storage = SecureTokenStorage()
                self.logger.info("安全令牌儲存已啟用")
            except Exception as e:
                self.logger.warning(f"無法啟用安全儲存: {e}")
        
        # 重試管理器
        self.retry_manager = None
        if enable_retry:
            retry_config = get_config('auth.retry', {})
            self.retry_manager = RetryManager(
                max_retries=retry_config.get('max_retries', 3),
                base_delay=retry_config.get('base_delay', 1.0),
                max_delay=retry_config.get('max_delay', 60.0)
            )
            self.logger.info("重試機制已啟用")
        
        # 狀態追蹤
        self._current_auth = None
        self._auth_history = []
        self._last_auth_time = None
        
        self.logger.info("增強認證管理器已初始化")
    
    @retry(max_retries=2, base_delay=1.0)
    def authenticate(self, 
                     auth_type: str = None,
                     force_refresh: bool = False,
                     **auth_params) -> AuthResult:
        """執行認證
        
        Args:
            auth_type: 指定認證類型，None 表示自動選擇
            force_refresh: 強制重新認證
            **auth_params: 認證參數
            
        Returns:
            認證結果
        """
        self.logger.info(f"開始認證流程 - 類型: {auth_type or '自動'}, 強制刷新: {force_refresh}")
        
        try:
            # 如果不強制刷新，先嘗試載入現有認證
            if not force_refresh:
                cached_auth = self._load_cached_auth(auth_type)
                if cached_auth:
                    return AuthResult(
                        success=True,
                        message="使用快取認證成功",
                        auth_type=type(cached_auth).__name__
                    )
            
            # 執行新的認證流程
            if auth_type:
                # 使用指定的認證類型
                auth_instance = self.auth_factory.create_auth(auth_type, **auth_params)
                success = auth_instance.authenticate(force_refresh)
                
                if success:
                    self._save_auth_instance(auth_instance)
                    result = AuthResult(
                        success=True,
                        message=f"{auth_type} 認證成功",
                        auth_type=auth_type
                    )
                else:
                    result = AuthResult(
                        success=False,
                        message=f"{auth_type} 認證失敗",
                        auth_type=auth_type
                    )
            else:
                # 使用策略管理器自動選擇
                result = self.strategy_manager.authenticate_with_strategy(**auth_params)
                
                if result.success:
                    current_auth = self.strategy_manager.get_current_auth()
                    if current_auth:
                        self._save_auth_instance(current_auth)
            
            # 記錄認證歷史
            self._record_auth_attempt(result)
            
            if result.success:
                self.logger.info(f"✅ 認證成功: {result.message}")
            else:
                self.logger.error(f"❌ 認證失敗: {result.message}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"認證過程發生異常: {e}")
            error_result = AuthResult(
                success=False,
                message=f"認證異常: {e}",
                error=e
            )
            self._record_auth_attempt(error_result)
            return error_result
    
    def _load_cached_auth(self, auth_type: str = None) -> Optional[BaseAuth]:
        """載入快取的認證
        
        Args:
            auth_type: 認證類型
            
        Returns:
            認證實例
        """
        try:
            # 優先使用內存快取
            if self._current_auth and self._current_auth.is_authenticated():
                if not auth_type or type(self._current_auth).__name__.lower().startswith(auth_type.lower()):
                    self.logger.debug("使用內存快取的認證")
                    return self._current_auth
            
            # 從安全儲存載入
            if self.secure_storage:
                # 如果指定了認證類型，直接載入
                if auth_type:
                    token_data = self.secure_storage.load_token(auth_type=auth_type)
                    if token_data:
                        # 重建認證實例
                        auth_instance = self.auth_factory.create_auth(auth_type)
                        auth_instance._credentials = token_data
                        auth_instance._authenticated = True
                        
                        # 驗證認證是否仍然有效
                        if auth_instance.is_authenticated():
                            self._current_auth = auth_instance
                            self.logger.info(f"從安全儲存載入 {auth_type} 認證成功")
                            return auth_instance
                else:
                    # 嘗試載入任何可用的認證
                    for preferred_type in self.preferred_auth_types:
                        token_data = self.secure_storage.load_token(auth_type=preferred_type)
                        if token_data:
                            auth_instance = self.auth_factory.create_auth(preferred_type)
                            auth_instance._credentials = token_data
                            auth_instance._authenticated = True
                            
                            if auth_instance.is_authenticated():
                                self._current_auth = auth_instance
                                self.logger.info(f"從安全儲存載入 {preferred_type} 認證成功")
                                return auth_instance
            
            return None
            
        except Exception as e:
            self.logger.warning(f"載入快取認證失敗: {e}")
            return None
    
    def _save_auth_instance(self, auth_instance: BaseAuth):
        """儲存認證實例
        
        Args:
            auth_instance: 認證實例
        """
        try:
            self._current_auth = auth_instance
            self._last_auth_time = datetime.now()
            
            # 儲存到安全儲存
            if self.secure_storage and auth_instance._credentials:
                auth_type = type(auth_instance).__name__.lower().replace('auth', '')
                
                # 取得使用者資訊
                user_info = {}
                try:
                    user_info = auth_instance.get_user_info() if hasattr(auth_instance, 'get_user_info') else {}
                except:
                    pass
                
                self.secure_storage.save_token(
                    auth_instance._credentials,
                    auth_type,
                    user_info.get('email'),
                    user_info
                )
                
                self.logger.debug(f"認證已儲存到安全儲存: {auth_type}")
            
        except Exception as e:
            self.logger.warning(f"儲存認證實例失敗: {e}")
    
    def _record_auth_attempt(self, result: AuthResult):
        """記錄認證嘗試
        
        Args:
            result: 認證結果
        """
        attempt_record = {
            'timestamp': datetime.now(),
            'success': result.success,
            'auth_type': result.auth_type,
            'message': result.message,
            'error': str(result.error) if result.error else None
        }
        
        self._auth_history.append(attempt_record)
        
        # 保持歷史記錄在合理範圍內
        max_history = get_config('auth.history_limit', 100)
        if len(self._auth_history) > max_history:
            self._auth_history = self._auth_history[-max_history:]
    
    def get_current_auth(self) -> Optional[BaseAuth]:
        """取得當前認證實例
        
        Returns:
            當前認證實例
        """
        if self._current_auth and self._current_auth.is_authenticated():
            return self._current_auth
        
        # 嘗試從策略管理器取得
        strategy_auth = self.strategy_manager.get_current_auth()
        if strategy_auth and strategy_auth.is_authenticated():
            self._current_auth = strategy_auth
            return strategy_auth
        
        return None
    
    def get_drive_service(self):
        """取得 Google Drive 服務
        
        Returns:
            Google Drive 服務實例
        """
        current_auth = self.get_current_auth()
        if not current_auth:
            # 嘗試自動認證
            result = self.authenticate()
            if not result.success:
                raise AuthenticationError("無法取得認證，請檢查認證配置")
            current_auth = self.get_current_auth()
        
        if current_auth:
            return current_auth.get_drive_service()
        else:
            raise AuthenticationError("無法取得 Drive 服務")
    
    def is_authenticated(self) -> bool:
        """檢查是否已認證
        
        Returns:
            是否已認證
        """
        current_auth = self.get_current_auth()
        return current_auth is not None and current_auth.is_authenticated()
    
    def logout(self):
        """登出並清理所有認證
        """
        self.logger.info("開始登出流程...")
        
        # 清理內存中的認證
        if self._current_auth:
            self._current_auth.logout()
        
        # 清理策略管理器
        self.strategy_manager.clear_cache()
        
        # 清理安全儲存（可選）
        if self.secure_storage:
            # 不自動清理安全儲存，讓使用者決定
            pass
        
        self._current_auth = None
        self._last_auth_time = None
        
        self.logger.info("登出完成")
    
    def get_auth_status(self) -> Dict[str, Any]:
        """取得認證狀態
        
        Returns:
            認證狀態資訊
        """
        current_auth = self.get_current_auth()
        
        status = {
            'authenticated': self.is_authenticated(),
            'current_auth_type': type(current_auth).__name__ if current_auth else None,
            'last_auth_time': self._last_auth_time.isoformat() if self._last_auth_time else None,
            'preferred_types': self.preferred_auth_types,
            'available_types': self.auth_factory.get_available_auth_types(),
            'strategy_status': self.strategy_manager.get_strategy_status(),
            'secure_storage_enabled': self.secure_storage is not None,
            'retry_enabled': self.retry_manager is not None,
            'auth_history_count': len(self._auth_history)
        }
        
        if current_auth:
            status['current_auth_info'] = current_auth.get_auth_info()
        
        return status
    
    def get_auth_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """取得認證歷史
        
        Args:
            limit: 返回記錄數量限制
            
        Returns:
            認證歷史記錄
        """
        return self._auth_history[-limit:] if limit > 0 else self._auth_history.copy()
    
    def cleanup_expired_tokens(self) -> int:
        """清理過期令牌
        
        Returns:
            清理的令牌數量
        """
        if self.secure_storage:
            return self.secure_storage.cleanup_expired_tokens()
        return 0
    
    def reset_auth_history(self):
        """重置認證歷史"""
        self._auth_history.clear()
        self.logger.info("認證歷史已重置")


# 全域增強認證管理器實例
enhanced_auth_manager = EnhancedAuthManager()


def quick_enhanced_auth(**kwargs) -> BaseAuth:
    """快速增強認證
    
    Args:
        **kwargs: 認證參數
        
    Returns:
        認證實例
    """
    result = enhanced_auth_manager.authenticate(**kwargs)
    if result.success:
        return enhanced_auth_manager.get_current_auth()
    else:
        raise AuthenticationError(f"快速認證失敗: {result.message}")


def get_enhanced_drive_service():
    """取得增強的 Drive 服務
    
    Returns:
        Google Drive 服務實例
    """
    return enhanced_auth_manager.get_drive_service() 