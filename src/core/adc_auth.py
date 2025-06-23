"""
Google Drive Application Default Credentials 認證模組
自動使用環境中的預設認證
"""

from google.auth import default
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .base_auth import BaseAuth
from ..utils.exceptions import AuthenticationError


class ADCAuth(BaseAuth):
    """Application Default Credentials 認證提供者
    
    自動使用環境中可用的認證：
    1. GOOGLE_APPLICATION_CREDENTIALS 環境變數
    2. gcloud CLI 認證
    3. Google Cloud 執行環境的中繼資料服務
    """
    
    def __init__(self, scopes: list = None):
        """
        初始化 ADC 認證
        
        Args:
            scopes: 權限範圍清單
        """
        super().__init__(scopes)
        self.logger.info("ADC 認證已初始化")
    
    def authenticate(self) -> bool:
        """執行 ADC 認證
        
        ADC 按以下優先順序尋找認證：
        1. GOOGLE_APPLICATION_CREDENTIALS 環境變數
        2. gcloud auth application-default login 使用者認證  
        3. Google Cloud 環境 metadata service
        4. Google Cloud SDK 預設專案服務帳戶
        
        Returns:
            認證是否成功
        """
        self.logger.info("開始 ADC 認證檢查...")
        
        # 檢查各種認證來源
        self._check_credential_sources()
        
        try:
            # 自動尋找可用的認證
            self.logger.info("執行 google.auth.default() 認證...")
            self._credentials, project = default(scopes=self.scopes)
            
            # 判斷使用的認證類型
            cred_type = type(self._credentials).__name__
            self.logger.info(f"使用認證類型: {cred_type}")
            
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
            
            self._authenticated = True
            self.logger.info(f"✅ ADC 認證成功 - 使用者: {user_email}")
            self.logger.info(f"專案 ID: {project}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ ADC 認證失敗: {e}")
            self._show_setup_suggestions()
            return False
    
    def _check_credential_sources(self):
        """檢查各種認證來源的狀態"""
        import os
        import shutil
        from pathlib import Path
        
        self.logger.info("🔍 檢查 ADC 認證來源...")
        
        # 1. 檢查 GOOGLE_APPLICATION_CREDENTIALS 環境變數
        gac = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if gac:
            if Path(gac).exists():
                self.logger.info(f"✅ 找到服務帳戶檔案: {gac}")
            else:
                self.logger.warning(f"⚠️ GOOGLE_APPLICATION_CREDENTIALS 設定但檔案不存在: {gac}")
        else:
            self.logger.info("ℹ️ GOOGLE_APPLICATION_CREDENTIALS 未設定")
        
        # 2. 檢查 gcloud CLI 認證
        gcloud_path = shutil.which('gcloud')
        if gcloud_path:
            self.logger.info(f"✅ 找到 gcloud CLI: {gcloud_path}")
            
            # 檢查 gcloud 認證狀態
            try:
                import subprocess
                result = subprocess.run(
                    ['gcloud', 'auth', 'list', '--format=json'], 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
                if result.returncode == 0:
                    import json
                    accounts = json.loads(result.stdout)
                    active_accounts = [acc for acc in accounts if acc.get('status') == 'ACTIVE']
                    if active_accounts:
                        self.logger.info(f"✅ 找到 {len(active_accounts)} 個活躍的 gcloud 帳戶")
                    else:
                        self.logger.info("ℹ️ 沒有活躍的 gcloud 帳戶")
                else:
                    self.logger.info("ℹ️ 無法檢查 gcloud 認證狀態")
            except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
                self.logger.info("ℹ️ 無法檢查 gcloud 認證狀態")
        else:
            self.logger.info("ℹ️ gcloud CLI 不在 PATH 中")
        
        # 3. 檢查是否在 Google Cloud 環境中
        try:
            import requests
            # 嘗試訪問 metadata 服務器（僅在 Google Cloud 環境中可用）
            metadata_url = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
            headers = {"Metadata-Flavor": "Google"}
            response = requests.get(metadata_url, headers=headers, timeout=1)
            if response.status_code == 200:
                self.logger.info("✅ 偵測到 Google Cloud 環境 metadata 服務")
            else:
                self.logger.info("ℹ️ 不在 Google Cloud 環境中")
        except:
            self.logger.info("ℹ️ 不在 Google Cloud 環境中")
    
    def _show_setup_suggestions(self):
        """顯示設定建議"""
        self.logger.info("💡 ADC 設定建議:")
        self.logger.info("  方法 1 (個人開發): gcloud auth application-default login")
        self.logger.info("  方法 2 (服務帳戶): 設定 GOOGLE_APPLICATION_CREDENTIALS 環境變數")
        self.logger.info("  方法 3 (Google Cloud): 在 GCE/GKE/Cloud Run 等環境中自動可用")
        self.logger.info("  詳細說明: 請參考 ADC使用指南.md")
    
    def get_drive_service(self):
        """取得 Google Drive 服務實例
        
        Returns:
            Google Drive 服務實例
        """
        if not self._drive_service:
            if not self.authenticate():
                raise AuthenticationError("ADC 認證失敗")
        
        return self._drive_service
    
    def is_authenticated(self) -> bool:
        """檢查是否已認證
        
        Returns:
            是否已認證
        """
        return self._credentials is not None and self._drive_service is not None


def create_adc_setup_guide() -> str:
    """創建 ADC 設定指南
    
    Returns:
        設定指南文字
    """
    guide = """
## ⚡ Application Default Credentials (ADC) 設定指南

### 方法 1：使用環境變數 (推薦)
```bash
# 設定環境變數指向服務帳戶檔案
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service_account.json"

# Windows
set GOOGLE_APPLICATION_CREDENTIALS=path\\to\\service_account.json
```

### 方法 2：使用 gcloud CLI
```bash
# 安裝 Google Cloud SDK
# 然後執行登入
gcloud auth login

# 設定應用程式預設認證
gcloud auth application-default login
```

### 方法 3：在 Google Cloud 環境中自動認證
- Compute Engine
- Google Kubernetes Engine (GKE)
- Cloud Run
- Cloud Functions
- App Engine

### 優點：
✅ **零配置**：環境設定好後完全自動
✅ **多環境支援**：本地開發到生產環境
✅ **統一認證**：所有 Google Cloud API 共用
✅ **安全性高**：不用在程式碼中寫死認證資訊

### 適用場景：
🎯 本地開發環境
🎯 CI/CD 管道
🎯 Google Cloud 部署
🎯 Docker 容器
    """
    
    return guide 