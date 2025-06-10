"""
Google Drive 認證管理系統
提供 OAuth 2.0 認證和服務存取功能
"""

import os
import pickle
from pathlib import Path
from typing import Optional, List, Any
import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..utils.logger import LoggerMixin
from ..utils.config import get_config
from ..utils.exceptions import AuthenticationError, ConfigurationError
from .adc_auth import ADCAuth


class GoogleOAuthProvider(LoggerMixin):
    """Google OAuth 提供者
    
    處理 Google OAuth 2.0 認證流程
    """
    
    def __init__(self, scopes: List[str] = None, credentials_file: str = None, token_file: str = None):
        self.scopes = scopes or get_config('auth.scopes', [
            'https://www.googleapis.com/auth/drive.readonly'
        ])
        self.credentials_file = credentials_file or get_config('auth.credentials_file', 'credentials.json')
        self.token_file = token_file or get_config('auth.token_file', 'token.pickle')
        
        self._credentials: Optional[Credentials] = None
        
        self.logger.info(f"OAuth 提供者初始化 - 範圍: {len(self.scopes)} 項")
    
    def _load_token(self) -> Optional[Credentials]:
        """載入儲存的認證令牌"""
        token_path = Path(self.token_file)
        
        if not token_path.exists():
            self.logger.debug(f"令牌檔案不存在: {token_path}")
            return None
        
        try:
            with open(token_path, 'rb') as token_file:
                credentials = pickle.load(token_file)
                self.logger.info("已載入儲存的認證令牌")
                return credentials
        except Exception as e:
            self.logger.error(f"載入令牌檔案失敗: {e}")
            return None
    
    def _save_token(self, credentials: Credentials):
        """儲存認證令牌"""
        try:
            # 確保目錄存在
            token_path = Path(self.token_file)
            token_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(token_path, 'wb') as token_file:
                pickle.dump(credentials, token_file)
                
            self.logger.info(f"認證令牌已儲存: {token_path}")
        except Exception as e:
            self.logger.error(f"儲存令牌失敗: {e}")
            raise AuthenticationError(f"無法儲存認證令牌: {e}")
    
    def _run_oauth_flow(self) -> Credentials:
        """執行 OAuth 認證流程"""
        credentials_path = Path(self.credentials_file)
        
        if not credentials_path.exists():
            raise ConfigurationError(
                'auth.credentials_file',
                f"認證檔案不存在: {credentials_path}"
            )
        
        try:
            # 確保正確讀取並清理 credentials.json 檔案（避免編碼問題）
            import json
            with open(credentials_path, 'r', encoding='utf-8') as f:
                client_config = json.load(f)
            
            # 清理可能有問題的 metadata 欄位
            if '_metadata' in client_config:
                self.logger.warning("檢測到 _metadata 欄位，可能含有問題數據，正在移除...")
                # 創建乾淨的 config 副本，排除有問題的欄位
                cleaned_config = {
                    key: value for key, value in client_config.items() 
                    if key != '_metadata' and not key.startswith('_')
                }
                client_config = cleaned_config
                self.logger.info("已清理 credentials 配置檔案")
            
            # 驗證必要欄位存在
            if 'installed' not in client_config and 'web' not in client_config:
                raise ConfigurationError(
                    'auth.credentials_file',
                    "credentials.json 格式不正確，缺少必要的認證資訊"
                )
            
            flow = InstalledAppFlow.from_client_config(
                client_config,
                self.scopes
            )
            
            # 動態尋找可用端口，避免端口沖突
            import socket
            from contextlib import closing
            
            def find_free_port():
                with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
                    s.bind(('', 0))
                    s.listen(1)
                    port = s.getsockname()[1]
                return port
            
            # 先嘗試配置的端口，如果失敗則使用隨機端口
            default_port = get_config('auth.port', 9876)
            
            try:
                credentials = flow.run_local_server(
                    port=default_port,
                    open_browser=True
                )
                self.logger.info(f"OAuth 認證流程完成 - 使用端口: {default_port}")
            except OSError as port_error:
                if "10048" in str(port_error):  # 端口被占用
                    free_port = find_free_port()
                    self.logger.warning(f"端口 {default_port} 被占用，使用端口: {free_port}")
                    credentials = flow.run_local_server(
                        port=free_port,
                        open_browser=True
                    )
                    self.logger.info(f"OAuth 認證流程完成 - 使用端口: {free_port}")
                else:
                    raise port_error
            
            return credentials
            
        except json.JSONDecodeError as e:
            self.logger.error(f"credentials.json 檔案格式錯誤: {e}")
            raise ConfigurationError(
                'auth.credentials_file',
                f"credentials.json 檔案不是有效的 JSON 格式: {e}"
            )
        except UnicodeDecodeError as e:
            self.logger.error(f"credentials.json 檔案編碼錯誤: {e}")
            self.logger.info("嘗試使用其他編碼方式讀取檔案...")
            # 嘗試用二進制模式讀取並清理
            try:
                with open(credentials_path, 'rb') as f:
                    raw_data = f.read()
                # 嘗試清理非 UTF-8 字符
                clean_data = raw_data.decode('utf-8', errors='replace')
                client_config = json.loads(clean_data)
                
                # 同樣清理 metadata
                if '_metadata' in client_config:
                    cleaned_config = {
                        key: value for key, value in client_config.items() 
                        if key != '_metadata' and not key.startswith('_')
                    }
                    client_config = cleaned_config
                
                flow = InstalledAppFlow.from_client_config(client_config, self.scopes)
                port = get_config('auth.port', 9876)
                credentials = flow.run_local_server(port=port, open_browser=True)
                self.logger.info("成功使用清理後的認證檔案完成認證")
                return credentials
                
            except Exception as fallback_error:
                raise ConfigurationError(
                    'auth.credentials_file',
                    f"無法讀取 credentials.json 檔案，請檢查檔案編碼: {e}\n備用方案也失敗: {fallback_error}"
                )
        except Exception as e:
            self.logger.error(f"OAuth 認證失敗: {e}")
            raise AuthenticationError(f"OAuth 認證失敗: {e}")
    
    def authenticate(self, force_refresh: bool = False) -> bool:
        """執行認證
        
        Args:
            force_refresh: 強制重新認證
            
        Returns:
            認證是否成功
        """
        try:
            if not force_refresh:
                # 嘗試載入現有令牌
                self._credentials = self._load_token()
            
            # 檢查令牌有效性
            if self._credentials and self._credentials.valid:
                self.logger.info("使用現有有效令牌")
                return True
            
            # 嘗試重新整理令牌
            if (self._credentials and 
                self._credentials.expired and 
                self._credentials.refresh_token):
                
                self.logger.info("嘗試重新整理令牌")
                try:
                    self._credentials.refresh(Request())
                    self._save_token(self._credentials)
                    self.logger.info("令牌重新整理成功")
                    return True
                except Exception as e:
                    self.logger.warning(f"令牌重新整理失敗: {e}")
            
            # 執行新的認證流程
            self.logger.info("開始新的認證流程")
            self._credentials = self._run_oauth_flow()
            self._save_token(self._credentials)
            
            return True
            
        except Exception as e:
            self.logger.error(f"認證失敗: {e}")
            self._credentials = None
            return False
    
    def get_credentials(self) -> Optional[Credentials]:
        """取得認證憑證"""
        if not self._credentials:
            self.logger.warning("尚未認證，嘗試自動認證")
            if not self.authenticate():
                return None
        
        return self._credentials
    
    def is_authenticated(self) -> bool:
        """檢查是否已認證"""
        return self._credentials is not None and self._credentials.valid
    
    def revoke_credentials(self):
        """撤銷認證"""
        if self._credentials:
            try:
                # 撤銷令牌
                self._credentials.revoke(Request())
                self.logger.info("認證已撤銷")
            except Exception as e:
                self.logger.warning(f"撤銷令牌失敗: {e}")
        
        # 清理本地檔案
        token_path = Path(self.token_file)
        if token_path.exists():
            token_path.unlink()
            self.logger.info("本地令牌檔案已刪除")
        
        self._credentials = None


class AuthManager(LoggerMixin):
    """認證管理器
    
    管理 Google Drive API 認證和服務建立
    支援多種認證方式，優先使用 ADC (Application Default Credentials)
    """
    
    def __init__(self, oauth_provider: GoogleOAuthProvider = None, prefer_adc: bool = True):
        self.oauth_provider = oauth_provider or GoogleOAuthProvider()
        self.prefer_adc = prefer_adc
        self.adc_auth = None
        self._drive_service = None
        self._service_cache = {}
        self._current_auth_method = None
        
        self.logger.info("認證管理器已初始化")
        if prefer_adc:
            self.logger.info("優先使用 ADC (Application Default Credentials)")
    
    def authenticate(self, force_refresh: bool = False) -> bool:
        """執行認證
        
        優先順序：
        1. ADC (如果啟用)
        2. OAuth 傳統流程
        
        Args:
            force_refresh: 強制重新認證
            
        Returns:
            認證是否成功
        """
        # 如果啟用 ADC 且非強制刷新，先嘗試 ADC
        if self.prefer_adc and not force_refresh:
            if self._try_adc_authentication():
                return True
            
            self.logger.info("ADC 認證失敗，回退到 OAuth 流程")
        
        # 使用傳統 OAuth 流程
        success = self.oauth_provider.authenticate(force_refresh)
        
        if success:
            self._current_auth_method = "oauth"
            # 清理服務快取，強制重建
            self._service_cache.clear()
            self._drive_service = None
            self.logger.info("OAuth 認證成功，服務快取已清理")
        else:
            self.logger.error("所有認證方式都失敗")
        
        return success
    
    def _try_adc_authentication(self) -> bool:
        """嘗試 ADC 認證
        
        Returns:
            ADC 認證是否成功
        """
        try:
            if not self.adc_auth:
                # 使用與 OAuth 相同的權限範圍
                scopes = get_config('auth.scopes', [
                    'https://www.googleapis.com/auth/drive.readonly'
                ])
                self.adc_auth = ADCAuth(scopes=scopes)
            
            if self.adc_auth.authenticate():
                self._current_auth_method = "adc"
                # 清理服務快取，強制重建
                self._service_cache.clear()
                self._drive_service = None
                self.logger.info("ADC 認證成功，服務快取已清理")
                return True
            
        except Exception as e:
            self.logger.debug(f"ADC 認證嘗試失敗: {e}")
        
        return False
    
    def get_drive_service(self):
        """取得 Google Drive 服務實例"""
        if self._drive_service is None:
            # 根據當前認證方式取得服務
            if self._current_auth_method == "adc" and self.adc_auth:
                self._drive_service = self.adc_auth.get_drive_service()
                self.logger.debug("Google Drive 服務已建立 (透過 ADC)")
            else:
                # 使用 OAuth 方式
                credentials = self.oauth_provider.get_credentials()
                
                if not credentials:
                    raise AuthenticationError("無法取得認證憑證，請先進行認證")
                
                try:
                    self._drive_service = build(
                        'drive', 
                        'v3', 
                        credentials=credentials,
                        cache_discovery=False
                    )
                    self.logger.debug("Google Drive 服務已建立 (透過 OAuth)")
                    
                except Exception as e:
                    self.logger.error(f"建立 Drive 服務失敗: {e}")
                    raise AuthenticationError(f"無法建立 Google Drive 服務: {e}")
        
        return self._drive_service
    
    def get_service(self, service_name: str, version: str = 'v3'):
        """取得指定的 Google API 服務
        
        Args:
            service_name: 服務名稱 (如 'drive', 'sheets')
            version: API 版本
            
        Returns:
            Google API 服務實例
        """
        cache_key = f"{service_name}_{version}"
        
        if cache_key not in self._service_cache:
            credentials = self.oauth_provider.get_credentials()
            
            if not credentials:
                raise AuthenticationError("無法取得認證憑證，請先進行認證")
            
            try:
                service = build(
                    service_name,
                    version,
                    credentials=credentials,
                    cache_discovery=False
                )
                self._service_cache[cache_key] = service
                self.logger.debug(f"Google {service_name} v{version} 服務已建立")
                
            except Exception as e:
                self.logger.error(f"建立 {service_name} 服務失敗: {e}")
                raise AuthenticationError(f"無法建立 Google {service_name} 服務: {e}")
        
        return self._service_cache[cache_key]
    
    def test_connection(self) -> bool:
        """測試 API 連線
        
        Returns:
            連線測試是否成功
        """
        try:
            drive_service = self.get_drive_service()
            
            # 嘗試取得使用者資訊
            about = drive_service.about().get(fields="user").execute()
            user_email = about.get('user', {}).get('emailAddress', 'Unknown')
            
            self.logger.info(f"API 連線測試成功 - 使用者: {user_email}")
            return True
            
        except HttpError as e:
            self.logger.error(f"API 連線測試失敗 - HTTP錯誤: {e}")
            return False
        except Exception as e:
            self.logger.error(f"API 連線測試失敗: {e}")
            return False
    
    def get_user_info(self) -> dict:
        """取得使用者資訊
        
        Returns:
            使用者資訊字典
        """
        try:
            drive_service = self.get_drive_service()
            about = drive_service.about().get(
                fields="user,storageQuota"
            ).execute()
            
            user_info = {
                'email': about.get('user', {}).get('emailAddress'),
                'display_name': about.get('user', {}).get('displayName'),
                'photo_link': about.get('user', {}).get('photoLink'),
                'storage_quota': about.get('storageQuota', {}),
                'is_authenticated': self.is_authenticated()
            }
            
            self.logger.debug(f"取得使用者資訊: {user_info['email']}")
            return user_info
            
        except Exception as e:
            self.logger.error(f"取得使用者資訊失敗: {e}")
            raise AuthenticationError(f"無法取得使用者資訊: {e}")
    
    def is_authenticated(self) -> bool:
        """檢查是否已認證"""
        if self._current_auth_method == "adc" and self.adc_auth:
            return self.adc_auth.is_authenticated()
        else:
            return self.oauth_provider.is_authenticated()
    
    def refresh_token(self) -> bool:
        """重新整理認證令牌
        
        Returns:
            重新整理是否成功
        """
        try:
            credentials = self.oauth_provider.get_credentials()
            
            if not credentials:
                self.logger.warning("沒有可用的認證憑證")
                return False
            
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                self.oauth_provider._save_token(credentials)
                
                # 清理服務快取
                self._service_cache.clear()
                self._drive_service = None
                
                self.logger.info("認證令牌已重新整理")
                return True
            else:
                self.logger.info("認證令牌仍然有效")
                return True
                
        except Exception as e:
            self.logger.error(f"重新整理令牌失敗: {e}")
            return False
    
    def logout(self):
        """登出並清理認證"""
        self.oauth_provider.revoke_credentials()
        self._service_cache.clear()
        self._drive_service = None
        self.logger.info("已登出並清理所有認證資料")
    
    def get_api_usage_info(self) -> dict:
        """取得 API 使用資訊（如果可用）
        
        Returns:
            API 使用統計
        """
        # 這裡可以實作 API 配額監控
        # 目前返回基本資訊
        return {
            'authenticated': self.is_authenticated(),
            'services_cached': len(self._service_cache),
            'drive_service_ready': self._drive_service is not None
        }


# 全域認證管理器實例
auth_manager = AuthManager()


def get_authenticated_service(service_name: str = 'drive', version: str = 'v3'):
    """便利函數：取得已認證的服務
    
    Args:
        service_name: 服務名稱
        version: API 版本
        
    Returns:
        Google API 服務實例
    """
    if not auth_manager.is_authenticated():
        if not auth_manager.authenticate():
            raise AuthenticationError("認證失敗，無法取得服務")
    
    if service_name == 'drive':
        return auth_manager.get_drive_service()
    else:
        return auth_manager.get_service(service_name, version)


def ensure_authenticated(func):
    """裝飾器：確保函數執行前已認證
    
    Args:
        func: 要裝飾的函數
        
    Returns:
        裝飾後的函數
    """
    def wrapper(*args, **kwargs):
        if not auth_manager.is_authenticated():
            if not auth_manager.authenticate():
                raise AuthenticationError("認證失敗，無法執行操作")
        
        return func(*args, **kwargs)
    
    return wrapper 