"""
統一認證工廠
提供統一的認證實例建立和管理介面
"""

from typing import Dict, Any, Optional, Type
from enum import Enum

from .base_auth import BaseAuth, AuthResult
from .adc_auth import ADCAuth
from .service_account_auth import ServiceAccountAuth
from .simple_auth import SimpleUserAuth
from ..utils.logger import LoggerMixin
from ..utils.exceptions import AuthenticationError, ConfigurationError
from ..utils.config import get_config


class AuthType(Enum):
    """支援的認證類型"""
    ADC = "adc"
    OAUTH = "oauth"
    SERVICE_ACCOUNT = "service_account"
    SIMPLE = "simple"


class AuthFactory(LoggerMixin):
    """統一認證工廠
    
    負責建立和管理不同類型的認證實例
    """
    
    # 註冊的認證提供者
    _providers: Dict[str, Type[BaseAuth]] = {
        AuthType.ADC.value: ADCAuth,
        AuthType.SERVICE_ACCOUNT.value: ServiceAccountAuth,
        AuthType.SIMPLE.value: SimpleUserAuth,
    }
    
    @classmethod
    def register_provider(cls, auth_type: str, provider_class: Type[BaseAuth]):
        """註冊新的認證提供者
        
        Args:
            auth_type: 認證類型標識
            provider_class: 認證提供者類別
        """
        cls._providers[auth_type] = provider_class
    
    @classmethod
    def get_available_auth_types(cls) -> list:
        """取得可用的認證類型清單
        
        Returns:
            認證類型清單
        """
        return list(cls._providers.keys())
    
    @classmethod
    def create_auth(cls, auth_type: str, **kwargs) -> BaseAuth:
        """建立認證實例
        
        Args:
            auth_type: 認證類型
            **kwargs: 認證參數
            
        Returns:
            認證實例
            
        Raises:
            ConfigurationError: 不支援的認證類型
        """
        if auth_type not in cls._providers:
            raise ConfigurationError(
                'auth_type',
                f"不支援的認證類型: {auth_type}。可用類型: {list(cls._providers.keys())}"
            )
        
        provider_class = cls._providers[auth_type]
        
        try:
            # 從配置檔案載入預設參數
            config_key = f"auth.{auth_type}"
            default_config = get_config(config_key, {})
            
            # 合併參數，kwargs 優先
            final_kwargs = {**default_config, **kwargs}
            
            instance = provider_class(**final_kwargs)
            
            # 記錄建立事件
            logger = LoggerMixin().logger
            logger.info(f"建立 {auth_type} 認證實例")
            
            return instance
            
        except Exception as e:
            raise AuthenticationError(f"建立 {auth_type} 認證實例失敗: {e}")
    
    @classmethod
    def auto_detect_auth(cls, prefer_order: list = None) -> Optional[BaseAuth]:
        """自動偵測可用的認證方式
        
        Args:
            prefer_order: 偏好的認證順序
            
        Returns:
            可用的認證實例，如果都不可用則返回 None
        """
        logger = LoggerMixin().logger
        
        # 預設偵測順序
        if prefer_order is None:
            prefer_order = [
                AuthType.ADC.value,
                AuthType.OAUTH.value,
                AuthType.SERVICE_ACCOUNT.value
            ]
        
        logger.info("開始自動偵測可用的認證方式...")
        
        for auth_type in prefer_order:
            if auth_type not in cls._providers:
                continue
            
            try:
                logger.info(f"嘗試 {auth_type} 認證...")
                auth_instance = cls.create_auth(auth_type)
                
                # 嘗試認證但不強制執行完整流程
                if cls._test_auth_availability(auth_instance):
                    logger.info(f"✅ 偵測到可用的認證方式: {auth_type}")
                    return auth_instance
                else:
                    logger.debug(f"❌ {auth_type} 認證不可用")
                    
            except Exception as e:
                logger.debug(f"❌ {auth_type} 認證偵測失敗: {e}")
        
        logger.warning("未偵測到任何可用的認證方式")
        return None
    
    @classmethod
    def _test_auth_availability(cls, auth_instance: BaseAuth) -> bool:
        """測試認證是否可用
        
        Args:
            auth_instance: 認證實例
            
        Returns:
            認證是否可用
        """
        try:
            # 對於不同類型進行不同的可用性檢查
            auth_type = type(auth_instance).__name__
            
            if auth_type == 'ADCAuth':
                # ADC 只需要檢查環境
                from google.auth import default
                try:
                    default()
                    return True
                except:
                    return False
            
            elif auth_type == 'ServiceAccountAuth':
                # 檢查服務帳戶檔案是否存在
                import os
                service_file = getattr(auth_instance, 'service_account_file', 'service_account.json')
                return os.path.exists(service_file)
            
            elif 'OAuth' in auth_type:
                # 檢查 credentials.json 是否存在
                import os
                cred_file = getattr(auth_instance, 'credentials_file', 'credentials.json')
                return os.path.exists(cred_file)
            
            return False
            
        except Exception:
            return False


class AuthStrategyManager(LoggerMixin):
    """認證策略管理器
    
    管理多種認證策略和自動切換
    """
    
    def __init__(self, strategies: list = None):
        """
        初始化策略管理器
        
        Args:
            strategies: 認證策略清單，按優先順序排列
        """
        self.strategies = strategies or [
            AuthType.ADC.value,
            AuthType.OAUTH.value,
            AuthType.SERVICE_ACCOUNT.value
        ]
        self._current_auth = None
        self._auth_cache = {}
        
        self.logger.info(f"認證策略管理器已初始化，策略順序: {self.strategies}")
    
    def authenticate_with_strategy(self, **kwargs) -> AuthResult:
        """使用策略進行認證
        
        Args:
            **kwargs: 認證參數
            
        Returns:
            認證結果
        """
        self.logger.info("開始策略認證...")
        
        last_error = None
        
        for strategy in self.strategies:
            try:
                self.logger.info(f"嘗試策略: {strategy}")
                
                # 檢查快取
                if strategy in self._auth_cache:
                    auth_instance = self._auth_cache[strategy]
                    if auth_instance.is_authenticated():
                        self.logger.info(f"使用快取的 {strategy} 認證")
                        self._current_auth = auth_instance
                        return AuthResult(
                            success=True,
                            message=f"使用快取的 {strategy} 認證成功",
                            auth_type=strategy
                        )
                
                # 建立新的認證實例
                auth_instance = AuthFactory.create_auth(strategy, **kwargs)
                
                # 嘗試認證
                if auth_instance.authenticate():
                    self.logger.info(f"✅ {strategy} 認證成功")
                    self._current_auth = auth_instance
                    self._auth_cache[strategy] = auth_instance
                    
                    return AuthResult(
                        success=True,
                        message=f"{strategy} 認證成功",
                        auth_type=strategy
                    )
                else:
                    self.logger.warning(f"❌ {strategy} 認證失敗")
                    
            except Exception as e:
                self.logger.error(f"❌ {strategy} 策略執行失敗: {e}")
                last_error = e
        
        # 所有策略都失敗
        error_msg = f"所有認證策略都失敗。最後錯誤: {last_error}"
        self.logger.error(error_msg)
        
        return AuthResult(
            success=False,
            message=error_msg,
            error=last_error
        )
    
    def get_current_auth(self) -> Optional[BaseAuth]:
        """取得當前認證實例
        
        Returns:
            當前認證實例
        """
        return self._current_auth
    
    def clear_cache(self):
        """清除認證快取"""
        self._auth_cache.clear()
        self.logger.info("認證快取已清除")
    
    def get_strategy_status(self) -> Dict[str, bool]:
        """取得各策略的狀態
        
        Returns:
            策略狀態字典
        """
        status = {}
        for strategy in self.strategies:
            try:
                if strategy in self._auth_cache:
                    status[strategy] = self._auth_cache[strategy].is_authenticated()
                else:
                    # 嘗試快速檢查可用性
                    auth_instance = AuthFactory.create_auth(strategy)
                    status[strategy] = AuthFactory._test_auth_availability(auth_instance)
            except:
                status[strategy] = False
        
        return status


# 全域工廠實例
auth_factory = AuthFactory()
auth_strategy_manager = AuthStrategyManager()


def quick_auth(auth_type: str = None, **kwargs) -> BaseAuth:
    """快速認證函數
    
    Args:
        auth_type: 指定的認證類型，如果為 None 則自動偵測
        **kwargs: 認證參數
        
    Returns:
        認證實例
        
    Raises:
        AuthenticationError: 認證失敗
    """
    if auth_type:
        # 使用指定的認證類型
        auth_instance = auth_factory.create_auth(auth_type, **kwargs)
        if auth_instance.authenticate():
            return auth_instance
        else:
            raise AuthenticationError(f"{auth_type} 認證失敗")
    else:
        # 使用策略管理器
        result = auth_strategy_manager.authenticate_with_strategy(**kwargs)
        if result.success:
            return auth_strategy_manager.get_current_auth()
        else:
            raise AuthenticationError(f"自動認證失敗: {result.message}")


def get_auth_status() -> Dict[str, Any]:
    """取得認證狀態資訊
    
    Returns:
        認證狀態字典
    """
    current_auth = auth_strategy_manager.get_current_auth()
    
    return {
        'available_types': auth_factory.get_available_auth_types(),
        'strategy_status': auth_strategy_manager.get_strategy_status(),
        'current_auth': current_auth.get_auth_info() if current_auth else None,
        'strategies': auth_strategy_manager.strategies
    } 