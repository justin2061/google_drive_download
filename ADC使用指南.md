# 🔐 ADC (Application Default Credentials) 使用指南

## 📋 什麼是 ADC？

Application Default Credentials (ADC) 是 Google 提供的自動認證機制，它會按照預定的優先順序自動尋找和使用認證：

1. **GOOGLE_APPLICATION_CREDENTIALS 環境變數** - 指向服務帳戶檔案
2. **gcloud auth application-default login 使用者認證** - 個人 Google 帳戶
3. **Google Cloud 環境 metadata service** - 雲端環境自動認證
4. **Google Cloud SDK 預設專案的服務帳戶** - SDK 預設設定

## 🚀 快速開始

### 方法 1：使用個人帳戶（推薦用於開發）

```bash
# 1. 安裝 Google Cloud SDK（如果尚未安裝）
# https://cloud.google.com/sdk/docs/install

# 2. 設定應用程式預設認證
gcloud auth application-default login

# 3. 運行您的應用程式，ADC 會自動使用這個認證
python your_app.py
```

### 方法 2：使用服務帳戶（推薦用於生產環境）

```bash
# 1. 下載服務帳戶 JSON 檔案（從 Google Cloud Console）

# 2. 設定環境變數
export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/service_account.json"

# Windows 使用者：
# set GOOGLE_APPLICATION_CREDENTIALS=path\to\your\service_account.json

# 3. 運行您的應用程式
python your_app.py
```

## 🔧 專案整合

您的專案現在已經整合了 ADC 支援！預設會：

1. **優先嘗試 ADC 認證**
2. **ADC 失敗時自動回退到傳統 OAuth 流程**
3. **自動偵測最適合的認證方式**

### 設定檔案

在 `config.yaml` 中：

```yaml
auth:
  prefer_adc: true  # 啟用 ADC 優先模式
  adc:
    fallback_to_oauth: true  # ADC 失敗時回退到 OAuth
```

### 程式碼使用

```python
# 無需修改現有程式碼！
from src.core.auth import auth_manager

# 認證管理器會自動嘗試 ADC
success = auth_manager.authenticate()

if success:
    drive = auth_manager.get_drive_service()
    # 使用 Drive API...
```

## 🛠 設定助手工具

使用內建的設定助手：

```bash
python scripts/setup_adc.py
```

這個工具會：
- ✅ 檢查 Google Cloud SDK 安裝狀態
- ✅ 檢查當前認證設定
- ✅ 引導您完成 ADC 設定
- ✅ 驗證設定是否正確

## 📊 認證狀態檢查

### 檢查 ADC 是否可用

```bash
# 檢查 ADC 狀態
gcloud auth application-default print-access-token

# 列出所有認證帳戶
gcloud auth list

# 檢查環境變數
echo $GOOGLE_APPLICATION_CREDENTIALS
```

### 在程式中檢查

```python
from src.core.auth import auth_manager

# 檢查是否已認證
if auth_manager.is_authenticated():
    print("✅ 認證成功")
    
    # 取得使用者資訊
    user_info = auth_manager.get_user_info()
    print(f"當前使用者: {user_info['email']}")
else:
    print("❌ 需要認證")
```

## 🌍 不同環境的使用

### 本地開發環境

```bash
# 使用個人帳戶
gcloud auth application-default login
```

### CI/CD 環境

```yaml
# GitHub Actions 範例
env:
  GOOGLE_APPLICATION_CREDENTIALS: ${{ secrets.GCP_SA_KEY }}

steps:
  - name: Set up Cloud SDK
    uses: google-github-actions/setup-gcloud@v0
    with:
      service_account_key: ${{ secrets.GCP_SA_KEY }}
```

### Docker 容器

```dockerfile
# 將服務帳戶檔案複製到容器
COPY service_account.json /app/
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/service_account.json
```

### Google Cloud 環境

在 Compute Engine、Cloud Run、GKE 等環境中，ADC 會自動使用環境提供的認證，無需額外設定。

## 🚨 故障排除

### 常見問題

1. **ADC 找不到認證**
   ```
   google.auth.exceptions.DefaultCredentialsError: Could not automatically determine credentials
   ```
   
   **解決方案：**
   - 確認已安裝 Google Cloud SDK
   - 執行 `gcloud auth application-default login`
   - 或設定 `GOOGLE_APPLICATION_CREDENTIALS` 環境變數

2. **權限不足**
   ```
   403 Forbidden: Insufficient Permission
   ```
   
   **解決方案：**
   - 確認帳戶有適當的 Google Drive API 權限
   - 檢查服務帳戶是否有存取目標檔案/資料夾的權限

3. **環境變數設定錯誤**
   ```
   FileNotFoundError: [Errno 2] No such file or directory
   ```
   
   **解決方案：**
   - 確認 `GOOGLE_APPLICATION_CREDENTIALS` 指向的檔案存在
   - 檢查檔案路徑是否正確

### 除錯模式

啟用詳細日誌：

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 現在會顯示詳細的認證過程
auth_manager.authenticate()
```

## 📈 最佳實踐

### 開發環境
- ✅ 使用 `gcloud auth application-default login`
- ✅ 使用個人 Google 帳戶
- ✅ 啟用除錯模式進行測試

### 測試環境
- ✅ 使用服務帳戶
- ✅ 設定 `GOOGLE_APPLICATION_CREDENTIALS` 環境變數
- ✅ 限制服務帳戶權限到最小必要範圍

### 生產環境
- ✅ 使用服務帳戶或 Google Cloud 環境認證
- ✅ 定期輪替服務帳戶金鑰
- ✅ 監控認證使用狀況
- ✅ 實施適當的錯誤處理和重試機制

## 🔄 從傳統 OAuth 遷移

如果您目前使用傳統的 OAuth 流程：

1. **無需改動程式碼** - 專案已經整合 ADC 支援
2. **設定 ADC** - 使用上述任一方法
3. **測試** - 確認應用程式使用 ADC 認證
4. **可選** - 停用 OAuth 回退（設定 `fallback_to_oauth: false`）

## 🎯 優勢總結

### ADC 的優勢

- **🎯 零配置** - 環境設定好後完全自動
- **🔄 多環境支援** - 從開發到生產無縫切換
- **🛡 安全性高** - 不需要在程式碼中硬編碼認證
- **⚡ 統一標準** - Google Cloud 生態系統的標準做法
- **🔧 易維護** - 簡化認證管理流程

### 與傳統 OAuth 的比較

| 特性 | 傳統 OAuth | ADC |
|------|-----------|-----|
| 設定複雜度 | 高 | 低 |
| 使用者互動 | 需要 | 可選 |
| 環境適應性 | 低 | 高 |
| 安全性 | 中 | 高 |
| 維護成本 | 高 | 低 |

現在您的 Google Drive 下載工具已經升級為使用現代化的 ADC 認證方式！🎉 