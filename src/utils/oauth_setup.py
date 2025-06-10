"""
動態 OAuth 設定模組
用於生成和管理 Google OAuth 應用程式設定
"""

import json
import os
from pathlib import Path
from typing import Dict, Any
from .logger import get_logger

logger = get_logger(__name__)


class OAuthSetupManager:
    """OAuth 設定管理器"""
    
    def __init__(self):
        self.credentials_file = "credentials.json"
        self.default_redirect_uris = [
            "http://localhost:8080/",
            "http://localhost:8080",
            "http://127.0.0.1:8080/",
            "http://127.0.0.1:8080"
        ]
    
    def generate_credentials_json(
        self, 
        client_id: str,
        client_secret: str,
        developer_email: str = "your.dev.email@gmail.com",
        app_name: str = "Google Drive 下載工具"
    ) -> Dict[str, Any]:
        """
        生成 credentials.json 內容
        
        Args:
            client_id: Google OAuth Client ID
            client_secret: Google OAuth Client Secret
            developer_email: 開發人員 Email
            app_name: 應用程式名稱
            
        Returns:
            credentials.json 的字典內容
        """
        credentials_data = {
            "installed": {
                "client_id": client_id,
                "project_id": "google-drive-downloader",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": client_secret,
                "redirect_uris": self.default_redirect_uris
            },
            "_metadata": {
                "developer_email": developer_email,
                "app_name": app_name,
                "generated_by": "Google Drive 下載工具",
                "version": "1.0"
            }
        }
        
        return credentials_data
    
    def save_credentials_file(
        self, 
        client_id: str,
        client_secret: str,
        developer_email: str = "your.dev.email@gmail.com",
        app_name: str = "Google Drive 下載工具",
        file_path: str = None
    ) -> bool:
        """
        儲存 credentials.json 檔案
        
        Args:
            client_id: Google OAuth Client ID
            client_secret: Google OAuth Client Secret
            developer_email: 開發人員 Email
            app_name: 應用程式名稱
            file_path: 檔案路徑，None 則使用預設路徑
            
        Returns:
            儲存是否成功
        """
        try:
            credentials_data = self.generate_credentials_json(
                client_id, client_secret, developer_email, app_name
            )
            
            target_file = file_path or self.credentials_file
            
            with open(target_file, 'w', encoding='utf-8') as f:
                json.dump(credentials_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"OAuth 設定檔已儲存: {target_file}")
            logger.info(f"開發人員: {developer_email}")
            logger.info(f"應用程式: {app_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"儲存 OAuth 設定檔失敗: {e}")
            return False
    
    def load_credentials_metadata(self, file_path: str = None) -> Dict[str, Any]:
        """
        載入 credentials.json 中的 metadata
        
        Args:
            file_path: 檔案路徑，None 則使用預設路徑
            
        Returns:
            metadata 字典
        """
        try:
            target_file = file_path or self.credentials_file
            
            if not Path(target_file).exists():
                return {}
            
            with open(target_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return data.get('_metadata', {})
            
        except Exception as e:
            logger.error(f"載入 OAuth 設定檔 metadata 失敗: {e}")
            return {}
    
    def create_sample_credentials(self) -> str:
        """
        創建範例 credentials.json 檔案說明
        
        Returns:
            範例檔案的說明文字
        """
        sample_text = """
## 如何取得 Google OAuth 認證設定

1. **前往 Google Cloud Console**
   - 訪問：https://console.cloud.google.com/

2. **建立或選擇專案**
   - 建立新專案或選擇現有專案

3. **啟用 Google Drive API**
   - 前往「API 和服務 > 程式庫」
   - 搜尋並啟用「Google Drive API」

4. **建立 OAuth 2.0 憑證**
   - 前往「API 和服務 > 憑證」
   - 點擊「建立憑證 > OAuth 2.0 用戶端 ID」
   - 選擇「桌面應用程式」
   - 設定名稱和重新導向 URI

5. **下載憑證檔案**
   - 下載 JSON 檔案
   - 或複製 Client ID 和 Client Secret

6. **在本應用中設定**
   - 輸入 Client ID 和 Client Secret
   - 設定開發人員 Email 和應用程式名稱
        """
        
        return sample_text
    
    def validate_oauth_config(self, client_id: str, client_secret: str) -> bool:
        """
        驗證 OAuth 設定
        
        Args:
            client_id: Google OAuth Client ID
            client_secret: Google OAuth Client Secret
            
        Returns:
            設定是否有效
        """
        if not client_id or not client_secret:
            return False
        
        # 基本格式檢查
        if not client_id.endswith('.apps.googleusercontent.com'):
            return False
        
        if len(client_secret) < 20:
            return False
        
        return True


# 全域實例
oauth_setup_manager = OAuthSetupManager() 