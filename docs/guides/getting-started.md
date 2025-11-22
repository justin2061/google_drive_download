# 從零開始：Google Drive 下載工具完整教學

本教學將帶您從零開始，一步步設定和使用 Google Drive 下載工具。

---

## 目錄

1. [環境需求](#1-環境需求)
2. [安裝步驟](#2-安裝步驟)
3. [認證設定](#3-認證設定)
4. [基本使用](#4-基本使用)
5. [進階功能](#5-進階功能)
6. [常見問題](#6-常見問題)

---

## 1. 環境需求

### 系統需求
- **作業系統**：Windows 10/11、macOS 10.14+、Linux
- **Python 版本**：3.8 或更高版本
- **磁碟空間**：至少 500MB（不含下載檔案）
- **網路連線**：穩定的網際網路連線

### 必要軟體
- Python 3.8+
- pip（Python 套件管理器）
- Git（可選，用於克隆專案）

### 檢查 Python 版本

```bash
python --version
# 或
python3 --version
```

如果未安裝 Python，請從 [python.org](https://www.python.org/downloads/) 下載安裝。

---

## 2. 安裝步驟

### 步驟 2.1：取得專案程式碼

**方法 A：使用 Git 克隆**
```bash
git clone https://github.com/your-username/google_drive_download.git
cd google_drive_download
```

**方法 B：下載 ZIP 檔案**
1. 前往專案 GitHub 頁面
2. 點擊綠色「Code」按鈕
3. 選擇「Download ZIP」
4. 解壓縮到您想要的位置

### 步驟 2.2：建立虛擬環境（建議）

虛擬環境可以隔離專案依賴，避免與其他 Python 專案衝突。

```bash
# 建立虛擬環境
python -m venv venv

# 啟動虛擬環境
# Windows:
venv\Scripts\activate

# macOS/Linux:
source venv/bin/activate
```

啟動後，命令列提示符會顯示 `(venv)` 前綴。

### 步驟 2.3：安裝依賴套件

```bash
pip install -r requirements.txt
```

安裝過程可能需要幾分鐘，視網路速度而定。

### 驗證安裝

```bash
python -c "import streamlit; import google.auth; print('安裝成功！')"
```

如果看到「安裝成功！」表示一切就緒。

---

## 3. 認證設定

使用 Google Drive API 需要認證。本工具支援三種認證方式：

| 認證方式 | 適用場景 | 難度 |
|---------|---------|-----|
| ADC（推薦） | 開發環境、個人使用 | ⭐ |
| OAuth 2.0 | 需要分享給他人使用 | ⭐⭐ |
| 服務帳戶 | 伺服器自動化、生產環境 | ⭐⭐⭐ |

### 方式 A：ADC 自動認證（推薦新手）

ADC（Application Default Credentials）是最簡單的認證方式。

#### 步驟 A.1：安裝 Google Cloud SDK

1. 前往 [Google Cloud SDK 下載頁面](https://cloud.google.com/sdk/docs/install)
2. 根據您的作業系統下載安裝程式
3. 執行安裝程式並按照指示完成安裝

#### 步驟 A.2：設定 ADC

```bash
# 登入您的 Google 帳戶
gcloud auth application-default login
```

瀏覽器會自動開啟，請選擇您的 Google 帳戶並授權。

#### 步驟 A.3：驗證設定

```bash
gcloud auth application-default print-access-token
```

如果看到一串 token，表示設定成功。

---

### 方式 B：OAuth 2.0 認證

如果您需要讓其他人使用這個工具，需要設定 OAuth 認證。

#### 步驟 B.1：建立 Google Cloud 專案

1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 點擊上方專案選單 → 「新增專案」
3. 輸入專案名稱（例如：`my-drive-downloader`）
4. 點擊「建立」

#### 步驟 B.2：啟用 Google Drive API

1. 在專案中，前往「API 和服務」→「程式庫」
2. 搜尋「Google Drive API」
3. 點擊進入後，點擊「啟用」

#### 步驟 B.3：建立 OAuth 憑證

1. 前往「API 和服務」→「憑證」
2. 點擊「建立憑證」→「OAuth 用戶端 ID」
3. 如果尚未設定同意畫面，點擊「設定同意畫面」
   - 選擇「外部」（或「內部」如果是 Google Workspace）
   - 填寫應用程式名稱和開發者 Email
   - 在「範圍」中添加 Google Drive API 相關權限
4. 回到憑證頁面，建立「桌面應用程式」類型的 OAuth 用戶端 ID
5. 下載 JSON 檔案，重新命名為 `credentials.json`
6. 將檔案放到專案根目錄

#### 步驟 B.4：首次執行授權

首次執行時，瀏覽器會開啟授權頁面：

```bash
python simple_backup.py
```

依照提示完成授權，token 會自動儲存。

---

### 方式 C：服務帳戶認證

適用於自動化腳本和伺服器環境。

#### 步驟 C.1：建立服務帳戶

1. 在 Google Cloud Console 中，前往「IAM 與管理」→「服務帳戶」
2. 點擊「建立服務帳戶」
3. 輸入名稱和描述
4. 點擊「建立並繼續」

#### 步驟 C.2：下載金鑰

1. 點擊新建立的服務帳戶
2. 切換到「金鑰」標籤
3. 點擊「新增金鑰」→「建立新金鑰」→ 選擇 JSON
4. 下載並安全保存金鑰檔案

#### 步驟 C.3：設定環境變數

```bash
# Windows
set GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\service-account.json

# macOS/Linux
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

> **注意**：服務帳戶預設無法存取您的個人 Google Drive。需要將檔案/資料夾分享給服務帳戶的 Email 地址。

---

## 4. 基本使用

認證設定完成後，您可以開始使用工具了。

### 4.1 簡化版命令列工具（推薦新手）

最簡單的使用方式：

```bash
python simple_backup.py
```

**操作流程：**

```
🚀 簡化版 Google Drive 備份工具
==================================================
🆕 新功能：自動轉換為 Office 格式

選擇操作:
1. 📁 下載整個資料夾
2. 📄 下載單一檔案
3. 🚪 退出

請選擇 (1-3): 1
```

1. 輸入 `1` 下載資料夾或 `2` 下載單一檔案
2. 貼上 Google Drive 連結或 ID
3. 選擇輸出目錄（按 Enter 使用預設）
4. 選擇是否轉換為 Office 格式

### 4.2 取得 Google Drive 連結

1. 在 Google Drive 中找到要下載的檔案/資料夾
2. 右鍵點擊 →「取得連結」
3. 複製連結

連結格式範例：
- 資料夾：`https://drive.google.com/drive/folders/1ABC...XYZ`
- 檔案：`https://drive.google.com/file/d/1ABC...XYZ/view`

### 4.3 Web 圖形介面

如果您偏好圖形化操作：

```bash
python run_streamlit.py
```

瀏覽器會自動開啟 Web 介面。

**功能特色：**
- 視覺化資料夾瀏覽
- 拖放式操作
- 即時下載進度
- 任務管理

### 4.4 Windows 一鍵啟動

Windows 使用者可以使用批次檔：

```bash
quick_backup.bat
```

提供快速選單啟動各種功能。

---

## 5. 進階功能

### 5.1 Office 格式自動轉換

下載時自動將 Google Workspace 文件轉換為 Office 格式：

| Google 檔案類型 | 轉換後格式 |
|---------------|----------|
| Google 文件 | Word (.docx) |
| Google 試算表 | Excel (.xlsx) |
| Google 簡報 | PowerPoint (.pptx) |
| Google 繪圖 | PNG (.png) |

啟用方式：
- 命令列：當詢問「是否轉換為 Office 格式？」時輸入 `Y`
- Web 介面：勾選「自動轉換為 Office 格式」

### 5.2 批次下載多個檔案

在 Web 介面中：
1. 瀏覽到目標資料夾
2. 勾選要下載的檔案
3. 點擊「建立下載任務」
4. 系統會批次處理所有選中的檔案

### 5.3 自訂下載設定

在 Web 介面的「下載管理」中可以設定：
- **並發下載數**：同時下載的檔案數量（1-10）
- **輸出目錄**：檔案儲存位置
- **包含子資料夾**：是否下載所有子資料夾內容

### 5.4 下載任務管理

Web 介面提供完整的任務管理功能：
- 查看所有進行中的任務
- 暫停/繼續下載
- 取消任務
- 查看下載歷史

---

## 6. 常見問題

### Q1：認證失敗怎麼辦？

**症狀**：出現「Could not automatically determine credentials」錯誤

**解決方案**：
1. 確認已執行 `gcloud auth application-default login`
2. 檢查網路連線
3. 嘗試重新執行認證命令

### Q2：無法存取檔案？

**症狀**：出現「403 Forbidden」或「File not found」錯誤

**解決方案**：
1. 確認您有該檔案的檢視權限
2. 檢查連結是否正確
3. 請檔案擁有者將檔案分享給您

### Q3：下載速度很慢？

**建議**：
1. 減少並發下載數量
2. 選擇網路較穩定的時段
3. 對於大量檔案，考慮使用 [Google Takeout](https://takeout.google.com/)

### Q4：程式卡住不動？

**解決方案**：
1. 按 `Ctrl+C` 終止程式
2. 重新啟動程式
3. 如果問題持續，嘗試使用簡化版工具

### Q5：如何備份整個 Google Drive？

對於完整備份，建議使用：
1. **Google Takeout**（官方工具）：https://takeout.google.com/
2. **rclone**（專業工具）：https://rclone.org/

---

## 下一步

恭喜您完成了基本設定！接下來可以：

1. 📖 閱讀 [ADC 使用指南](./adc-guide.md) 了解更多認證細節
2. 🔄 閱讀 [Office 格式轉換說明](./office-conversion.md) 了解轉換功能
3. 🔧 閱讀 [備份方案比較](./backup-options.md) 選擇最適合您的方式

---

## 取得幫助

如果遇到問題：
1. 查看本文件的「常見問題」章節
2. 查看專案的 [GitHub Issues](https://github.com/your-username/google_drive_download/issues)
3. 提交新的 Issue 描述您的問題

---

**祝您使用愉快！** 🚀
