"""
Google Drive Service Account 認證模組
提供無需使用者互動的認證方式
"""

import json
from pathlib import Path
from typing import Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .base_auth import BaseAuth
from ..utils.exceptions import AuthenticationError, ConfigurationError


class ServiceAccountAuth(BaseAuth):
    """Service Account 認證提供者
    
    使用服務帳戶進行認證，無需使用者互動
    適用於自動化工具和伺服器端應用
    """
    
    def __init__(self, service_account_file: str = None, scopes: list = None):
        """
        初始化 Service Account 認證
        
        Args:
            service_account_file: 服務帳戶 JSON 檔案路徑
            scopes: 權限範圍清單
        """
        default_scopes = scopes or [
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/drive.file'
        ]
        super().__init__(default_scopes)
        self.service_account_file = service_account_file or 'service_account.json'
        
        self.logger.info("Service Account 認證已初始化")
    
    def authenticate(self) -> bool:
        """執行 Service Account 認證
        
        Returns:
            認證是否成功
        """
        try:
            # 檢查服務帳戶檔案是否存在
            service_file_path = Path(self.service_account_file)
            if not service_file_path.exists():
                raise ConfigurationError(
                    'service_account_file',
                    f"服務帳戶檔案不存在: {service_file_path}"
                )
            
            # 載入服務帳戶憑證
            self._credentials = service_account.Credentials.from_service_account_file(
                str(service_file_path), 
                scopes=self.scopes
            )
            
            # 建立 Drive 服務
            self._drive_service = build(
                'drive', 
                'v3', 
                credentials=self._credentials,
                cache_discovery=False
            )
            
            # 測試連線
            about = self._drive_service.about().get(fields="user").execute()
            user_email = about.get('user', {}).get('emailAddress', 'Unknown')
            
            self.logger.info(f"Service Account 認證成功 - 服務帳戶: {user_email}")
            return True
            
        except FileNotFoundError:
            self.logger.error(f"找不到服務帳戶檔案: {self.service_account_file}")
            return False
        except json.JSONDecodeError as e:
            self.logger.error(f"服務帳戶檔案格式錯誤: {e}")
            return False
        except HttpError as e:
            self.logger.error(f"Google API 錯誤: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Service Account 認證失敗: {e}")
            return False
    
    def get_drive_service(self):
        """取得 Google Drive 服務實例
        
        Returns:
            Google Drive 服務實例
        """
        if not self._drive_service:
            if not self.authenticate():
                raise AuthenticationError("Service Account 認證失敗")
        
        return self._drive_service
    
    def is_authenticated(self) -> bool:
        """檢查是否已認證
        
        Returns:
            是否已認證
        """
        return self._credentials is not None and self._drive_service is not None
    
    def get_user_info(self) -> dict:
        """取得服務帳戶資訊
        
        Returns:
            服務帳戶資訊
        """
        try:
            if not self._drive_service:
                raise AuthenticationError("尚未認證")
            
            about = self._drive_service.about().get(
                fields="user,storageQuota"
            ).execute()
            
            return {
                'email': about.get('user', {}).get('emailAddress'),
                'display_name': about.get('user', {}).get('displayName', 'Service Account'),
                'account_type': 'service_account',
                'storage_quota': about.get('storageQuota', {}),
                'is_authenticated': True
            }
            
        except Exception as e:
            self.logger.error(f"取得服務帳戶資訊失敗: {e}")
            raise AuthenticationError(f"無法取得服務帳戶資訊: {e}")


def create_service_account_setup_guide() -> str:
    """創建 Service Account 設定指南
    
    Returns:
        設定指南文字
    """
    guide = """
## 🔧 Service Account 設定指南

### 步驟 1：建立 Service Account
1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 選擇或建立專案
3. 啟用 Google Drive API
4. 前往「IAM 和管理 > 服務帳戶」
5. 點擊「建立服務帳戶」
6. 輸入服務帳戶名稱和描述
7. 點擊「建立並繼續」

### 步驟 2：下載憑證檔案
1. 在服務帳戶清單中，點擊剛建立的服務帳戶
2. 切換到「金鑰」分頁
3. 點擊「新增金鑰 > 建立新金鑰」
4. 選擇「JSON」格式
5. 下載並重新命名為 `service_account.json`
6. 將檔案放在專案根目錄

### 步驟 3：授權 Drive 存取權限
1. 複製服務帳戶的 Email 地址
2. 在 Google Drive 中分享要存取的資料夾
3. 將服務帳戶 Email 新增為協作者
4. 設定適當的權限（檢視者/編輯者/擁有者）

### 優點：
✅ 無需使用者授權流程
✅ 不會過期的認證
✅ 適合自動化腳本
✅ 伺服器端應用的最佳選擇

### 限制：
⚠️ 只能存取明確分享的檔案/資料夾
⚠️ 不是個人使用者帳戶
⚠️ 需要手動設定權限
    """
    
    return guide


# 便利函數
def get_service_account_drive_service(service_account_file: str = None):
    """便利函數：快速取得 Service Account Drive 服務
    
    Args:
        service_account_file: 服務帳戶檔案路徑
        
    Returns:
        Google Drive 服務實例
    """
    auth = ServiceAccountAuth(service_account_file)
    return auth.get_drive_service() 