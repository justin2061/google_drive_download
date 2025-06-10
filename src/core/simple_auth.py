"""
簡化的 Google Drive 使用者認證模組
減少配置步驟，提供更簡單的認證體驗
"""

import os
import pickle
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from ..utils.logger import LoggerMixin
from ..utils.exceptions import AuthenticationError


class SimpleUserAuth(LoggerMixin):
    """簡化的使用者認證
    
    自動處理常見的認證場景，減少配置複雜度
    """
    
    # 預定義的常用權限範圍
    SCOPES_READONLY = ['https://www.googleapis.com/auth/drive.readonly']
    SCOPES_FILE = ['https://www.googleapis.com/auth/drive.file']
    SCOPES_FULL = ['https://www.googleapis.com/auth/drive']
    
    def __init__(self, 
                 client_id: str = None,
                 client_secret: str = None,
                 scopes: str = 'readonly',
                 token_file: str = 'token.pickle'):
        """
        初始化簡化認證
        
        Args:
            client_id: Google OAuth Client ID
            client_secret: Google OAuth Client Secret  
            scopes: 權限範圍 ('readonly', 'file', 'full')
            token_file: 令牌儲存檔案
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_file = token_file
        
        # 設定權限範圍
        scope_mapping = {
            'readonly': self.SCOPES_READONLY,
            'file': self.SCOPES_FILE,
            'full': self.SCOPES_FULL
        }
        self.scopes = scope_mapping.get(scopes, self.SCOPES_READONLY)
        
        self._credentials = None
        self._drive_service = None
        
        self.logger.info(f"簡化認證已初始化 - 權限: {scopes}")
    
    def quick_setup(self, client_id: str, client_secret: str) -> bool:
        """快速設定認證
        
        Args:
            client_id: Google OAuth Client ID
            client_secret: Google OAuth Client Secret
            
        Returns:
            設定是否成功
        """
        self.client_id = client_id
        self.client_secret = client_secret
        
        # 立即嘗試認證
        return self.authenticate()
    
    def authenticate(self) -> bool:
        """執行認證流程
        
        Returns:
            認證是否成功
        """
        try:
            # 嘗試載入現有令牌
            self._credentials = self._load_token()
            
            # 檢查令牌有效性
            if self._credentials and self._credentials.valid:
                self.logger.info("使用現有有效令牌")
                return self._build_service()
            
            # 嘗試重新整理令牌
            if (self._credentials and 
                self._credentials.expired and 
                self._credentials.refresh_token):
                
                self.logger.info("重新整理過期令牌")
                self._credentials.refresh(Request())
                self._save_token()
                return self._build_service()
            
            # 執行新的認證流程
            if not self.client_id or not self.client_secret:
                self.logger.error("缺少 Client ID 或 Client Secret")
                return False
            
            self.logger.info("開始新的認證流程")
            self._credentials = self._run_oauth_flow()
            self._save_token()
            return self._build_service()
            
        except Exception as e:
            self.logger.error(f"認證失敗: {e}")
            return False
    
    def _load_token(self) -> Optional[Credentials]:
        """載入儲存的令牌"""
        token_path = Path(self.token_file)
        
        if not token_path.exists():
            return None
        
        try:
            with open(token_path, 'rb') as token_file:
                return pickle.load(token_file)
        except Exception as e:
            self.logger.warning(f"載入令牌失敗: {e}")
            return None
    
    def _save_token(self):
        """儲存令牌"""
        try:
            token_path = Path(self.token_file)
            token_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(token_path, 'wb') as token_file:
                pickle.dump(self._credentials, token_file)
                
            self.logger.info("認證令牌已儲存")
        except Exception as e:
            self.logger.error(f"儲存令牌失敗: {e}")
    
    def _run_oauth_flow(self) -> Credentials:
        """執行 OAuth 流程"""
        # 建立臨時的 credentials.json
        temp_creds = {
            "installed": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost:8080"]
            }
        }
        
        import tempfile
        import json
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(temp_creds, f)
            temp_file = f.name
        
        try:
            flow = InstalledAppFlow.from_client_secrets_file(temp_file, self.scopes)
            
            # 使用本地伺服器進行認證
            credentials = flow.run_local_server(
                port=0,  # 自動選擇可用端口
                open_browser=True
            )
            
            return credentials
            
        finally:
            # 清理臨時檔案
            try:
                os.unlink(temp_file)
            except:
                pass
    
    def _build_service(self) -> bool:
        """建立 Drive 服務"""
        try:
            self._drive_service = build(
                'drive', 
                'v3', 
                credentials=self._credentials,
                cache_discovery=False
            )
            
            # 測試連線
            about = self._drive_service.about().get(fields="user").execute()
            user_email = about.get('user', {}).get('emailAddress', 'Unknown')
            
            self.logger.info(f"Drive 服務已建立 - 使用者: {user_email}")
            return True
            
        except Exception as e:
            self.logger.error(f"建立 Drive 服務失敗: {e}")
            return False
    
    def get_drive_service(self):
        """取得 Google Drive 服務實例
        
        Returns:
            Google Drive 服務實例
        """
        if not self._drive_service:
            if not self.authenticate():
                raise AuthenticationError("認證失敗")
        
        return self._drive_service
    
    def is_authenticated(self) -> bool:
        """檢查是否已認證
        
        Returns:
            是否已認證
        """
        return self._credentials is not None and self._drive_service is not None
    
    def logout(self):
        """登出並清理認證"""
        if self._credentials:
            try:
                self._credentials.revoke(Request())
            except:
                pass
        
        # 清理本地檔案
        token_path = Path(self.token_file)
        if token_path.exists():
            token_path.unlink()
        
        self._credentials = None
        self._drive_service = None
        
        self.logger.info("已登出")


# 便利函數
def quick_auth(client_id: str, client_secret: str, scopes: str = 'readonly'):
    """快速認證函數
    
    Args:
        client_id: Google OAuth Client ID
        client_secret: Google OAuth Client Secret
        scopes: 權限範圍 ('readonly', 'file', 'full')
        
    Returns:
        Google Drive 服務實例
    """
    auth = SimpleUserAuth(scopes=scopes)
    if auth.quick_setup(client_id, client_secret):
        return auth.get_drive_service()
    else:
        raise AuthenticationError("快速認證失敗")


def create_simple_auth_guide() -> str:
    """創建簡化認證指南
    
    Returns:
        設定指南文字
    """
    guide = """
## 🚀 簡化認證使用指南

### 快速開始（3行程式碼）
```python
from src.core.simple_auth import quick_auth

# 一行程式碼完成認證
drive = quick_auth("your_client_id", "your_client_secret", "readonly")

# 直接使用
files = drive.files().list().execute()
```

### 進階使用
```python
from src.core.simple_auth import SimpleUserAuth

# 建立認證實例
auth = SimpleUserAuth(scopes='file')  # readonly, file, full

# 設定認證資訊
success = auth.quick_setup("client_id", "client_secret")

if success:
    drive = auth.get_drive_service()
    # 使用 Drive API
```

### 權限範圍說明
- **readonly**: 只能讀取檔案（推薦）
- **file**: 可以建立和修改 App 建立的檔案
- **full**: 完整的 Drive 存取權限

### 特點
✅ **3行程式碼**：最少程式碼完成認證
✅ **自動重新整理**：令牌過期自動處理
✅ **智慧快取**：避免重複認證
✅ **錯誤處理**：完整的異常處理機制
✅ **彈性權限**：預定義常用權限範圍

### 適用場景
🎯 快速原型開發
🎯 簡單的個人工具
🎯 學習和測試
🎯 不需要複雜配置的應用
    """
    
    return guide 