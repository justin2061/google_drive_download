# 🚀 Google Drive 下載工具

一個功能完整的 Google Drive 檔案下載工具，支援**自動轉換為 Office 格式**，提供命令行和 Web 介面兩種使用方式。

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## ✨ 主要功能

### 🔄 **自動 Office 格式轉換** (新功能)
- 📝 **Google 文件** → Word (.docx)
- 📊 **Google 試算表** → Excel (.xlsx)
- 📽️ **Google 簡報** → PowerPoint (.pptx)
- 🎨 **Google 繪圖** → PNG 圖片 (.png)
- 📋 **Google 表單** → ZIP 檔案 (.zip)

### 📥 **強大的下載功能**
- ✅ 單一檔案下載
- ✅ 整個資料夾下載（包含子資料夾）
- ✅ 批次下載多個檔案
- ✅ 斷點續傳和重試機制
- ✅ 進度顯示和狀態追蹤

### 🔐 **靈活的認證方式**
- ✅ **ADC 自動認證**（推薦）
- ✅ **OAuth 2.0 認證**
- ✅ **服務帳戶認證**
- ✅ 多種認證來源自動檢測

### 🎛️ **多種使用介面**
- 🖥️ **Streamlit Web 介面**（圖形化操作）
- ⌨️ **命令行介面**（腳本自動化）
- 📦 **一鍵執行腳本**（快速啟動）

## 📚 文件資源

完整的文件已整理至 `docs/` 資料夾：

- **[📖 從零開始教學](docs/guides/getting-started.md)** - 新手必讀，完整的安裝和使用教學
- **[🔐 ADC 認證指南](docs/guides/adc-guide.md)** - Google 認證設定詳解
- **[🔄 Office 格式轉換](docs/guides/office-conversion.md)** - 自動轉換功能說明
- **[📋 備份方案比較](docs/guides/backup-options.md)** - 各種備份方式的優缺點
- **[📁 完整文件索引](docs/README.md)** - 所有文件的目錄

---

## 🚀 快速開始

### 1. 安裝依賴套件

```bash
# 克隆專案
git clone https://github.com/your-username/google_drive_download.git
cd google_drive_download

# 安裝 Python 套件
pip install -r requirements.txt
```

### 2. 認證設定

選擇以下任一認證方式：

#### 方式 A：ADC 自動認證（推薦）

```bash
# 安裝 Google Cloud SDK
# 下載：https://cloud.google.com/sdk/docs/install

# 登入 Google 帳戶
gcloud auth application-default login

# 驗證設定
gcloud auth application-default print-access-token
```

#### 方式 B：OAuth 認證

1. 到 [Google Cloud Console](https://console.cloud.google.com/)
2. 創建新專案或選擇現有專案
3. 啟用 Google Drive API
4. 創建 OAuth 2.0 憑證
5. 下載 `credentials.json` 到專案根目錄

#### 方式 C：服務帳戶認證

1. 在 Google Cloud Console 創建服務帳戶
2. 下載 JSON 金鑰檔案
3. 設定環境變數：
   ```bash
   # Windows
   set GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\service-account.json
   
   # Linux/Mac
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
   ```

### 3. 開始使用

```bash
# 方式 1：一鍵啟動（推薦）
quick_backup.bat

# 方式 2：簡化版命令行工具
python simple_backup.py

# 方式 3：Web 介面
python run_streamlit.py
```

## 📖 詳細使用指南

### 🎯 簡化版命令行工具

最簡單的使用方式，適合快速備份：

```bash
python simple_backup.py
```

**使用流程：**
1. 選擇 `1. 📁 下載整個資料夾` 或 `2. 📄 下載單一檔案`
2. 輸入 Google Drive URL 或檔案 ID
3. 選擇輸出目錄（可留空使用預設）
4. 選擇是否轉換為 Office 格式：`是否轉換為 Office 格式？(Y/n):`
   - 直接按 Enter 或輸入 `y` → **自動轉換**
   - 輸入 `n` → 保持原格式

**範例操作：**
```
🚀 簡化版 Google Drive 備份工具
==================================================
🆕 新功能：自動轉換為 Office 格式
   📝 Google文件 → Word (.docx)
   📊 Google試算表 → Excel (.xlsx)  
   📽️ Google簡報 → PowerPoint (.pptx)
==================================================

選擇操作:
1. 📁 下載整個資料夾
2. 📄 下載單一檔案
3. 🚪 退出

請選擇 (1-3): 1
請輸入資料夾 URL 或 ID: https://drive.google.com/drive/folders/1ABC...
輸出目錄 (留空使用預設): 
是否轉換為 Office 格式？(Y/n): 

📁 正在分析資料夾...
📂 資料夾名稱: 我的專案
🔍 正在取得檔案清單...
📄 找到 15 個檔案

📊 檔案分析:
📝 Google Workspace 檔案: 8 個
📄 一般檔案: 7 個

🔄 將自動轉換為 Office 格式:
   → 3 個檔案將轉為 Word 文件 (.docx)
   → 2 個檔案將轉為 Excel 試算表 (.xlsx)
   → 3 個檔案將轉為 PowerPoint 簡報 (.pptx)

💾 總大小: 45.2 MB

是否要下載這 15 個檔案到 'backup_20241205_143022' (自動轉換為 Office 格式)？ (y/N): y

🚀 開始下載到 backup_20241205_143022
[1/15] 📥 專案提案書
    🔄 轉換為 Word 文件 (.docx)
    ✅ 完成 (245.7 KB)
[2/15] 📥 預算表
    🔄 轉換為 Excel 試算表 (.xlsx)
    ✅ 完成 (89.3 KB)
...

📊 下載完成!
✅ 成功: 15 個檔案
🔄 轉換: 8 個 Google Workspace 檔案
❌ 失敗: 0 個檔案
📁 儲存位置: D:\downloads\backup_20241205_143022
```

### 🌐 Streamlit Web 介面

提供完整的圖形化操作介面：

```bash
python run_streamlit.py
```

**功能特色：**

#### 🔐 認證頁面
- **智能認證**：自動檢測 ADC → OAuth 認證
- **強制 OAuth**：手動執行 OAuth 流程
- **ADC 設定指南**：詳細的設定說明
- **自訂 OAuth 憑證**：支援自訂開發者資訊

#### 📁 資料夾瀏覽
- **視覺化瀏覽**：類似檔案管理員的介面
- **麵包屑導航**：清楚顯示當前位置
- **搜尋和篩選**：依名稱、類型、大小篩選
- **卡片/表格視圖**：兩種顯示模式
- **即時預覽**：查看資料夾內容統計

#### 📥 下載管理
- **拖放支援**：支援 URL 貼上
- **進階設定**：
  - ✅ **自動轉換為 Office 格式**（預設開啟）
  - 🔧 並發下載數控制
  - 📁 自訂輸出目錄
  - 🔄 包含子資料夾選項

#### 📋 任務管理
- **即時監控**：下載進度即時顯示
- **任務控制**：開始、暫停、取消、刪除
- **統計圖表**：視覺化任務狀態
- **詳細資訊**：檔案清單、錯誤記錄

### ⚡ 一鍵啟動腳本

Windows 批次檔提供快速啟動選項：

```bash
quick_backup.bat
```

**選項說明：**
1. **🎯 執行簡化版備份工具**：啟動命令行版本
2. **📖 開啟備份方案說明**：查看詳細說明文檔
3. **🌐 開啟 Google Takeout**：Google 官方備份服務
4. **📁 開啟 rclone 官網**：專業同步工具
5. **🔄 重新啟動 Streamlit 應用**：重啟 Web 介面
6. **❌ 退出**

## 🔧 進階設定

### 🎨 自訂 OAuth 設定

在 Streamlit 介面中可以設定：

1. **OAuth 憑證**：
   - Client ID
   - Client Secret

2. **開發者資訊**：
   - 開發者 Email
   - 應用程式名稱

3. **自動生成 credentials.json**

### 📊 檔案格式選項

支援多種匯出格式：

| Google Workspace 類型 | 可用格式 |
|---------------------|---------|
| Google 文件 | docx, pdf, txt, html |
| Google 試算表 | xlsx, csv, pdf, html |
| Google 簡報 | pptx, pdf, txt, html |
| Google 繪圖 | png, jpg, pdf, svg |
| Google 表單 | zip |

### 🔄 重試和錯誤處理

系統自動處理：
- **網路連接問題**：自動重試最多 3 次
- **API 限制**：指數退避重試策略
- **大型檔案**：分塊下載機制
- **SSL 錯誤**：多種憑證驗證策略

## 📁 專案結構

```
google_drive_download/
├── src/                          # 核心原始碼
│   ├── core/                     # 核心功能模組
│   │   ├── auth.py              # 認證管理
│   │   ├── file_handler.py      # 檔案處理和轉換
│   │   ├── downloader.py        # 下載管理
│   │   └── progress.py          # 進度追蹤
│   ├── utils/                    # 工具模組
│   │   ├── config.py            # 設定管理
│   │   ├── logger.py            # 日誌系統
│   │   └── oauth_setup.py       # OAuth 設定
│   └── cli/                      # 命令行介面
│       └── main.py              # CLI 入口點
├── ui/                           # Web 介面
│   └── streamlit_app.py         # Streamlit 應用
├── config/                       # 設定檔案
│   └── default.yaml             # 預設設定
├── simple_backup.py              # 簡化版工具
├── run_streamlit.py             # Web 介面啟動器
├── quick_backup.bat             # 一鍵啟動腳本
├── requirements.txt             # Python 依賴
└── README.md                    # 說明文檔
```

## 🛠️ 依賴套件

主要依賴：
```
google-api-python-client>=2.0.0   # Google API 客戶端
google-auth>=2.0.0                # Google 認證
google-auth-oauthlib>=0.5.0       # OAuth 流程
streamlit>=1.28.0                 # Web 介面框架
pandas>=1.5.0                     # 資料處理
plotly>=5.0.0                     # 圖表展示
requests>=2.28.0                  # HTTP 請求
PyYAML>=6.0                       # YAML 設定檔支援
```

完整依賴清單請查看 `requirements.txt`。

## 🔒 安全性和隱私

### 🛡️ 資料保護
- ✅ **本地處理**：所有檔案處理均在本地電腦進行
- ✅ **無資料傳輸**：不會將檔案上傳到外部伺服器
- ✅ **安全認證**：使用 Google 官方認證機制
- ✅ **權限最小化**：僅請求必要的讀取權限

### 🔐 認證安全
- **OAuth 2.0**：業界標準認證協議
- **本地儲存**：認證令牌安全儲存在本地
- **定期更新**：自動處理令牌更新
- **可撤銷**：可隨時在 Google 帳戶中撤銷授權

### 📋 權限說明
本應用僅請求以下權限：
- **Google Drive 讀取權限**：用於瀏覽和下載檔案
- **基本個人資料**：顯示使用者名稱和 Email

## 🆘 常見問題

### Q: 為什麼下載的檔案格式和 Google Drive 中不同？
A: Google Workspace 檔案（如 Google 文件）無法直接下載，需要轉換為標準格式。預設會轉換為 Office 格式以便使用。

### Q: 下載大型資料夾時應用程式卡住怎麼辦？
A: 
1. 重新整理瀏覽器頁面
2. 重新啟動應用程式：`quick_backup.bat` → 選項 5
3. 使用簡化版工具：系統已優化處理大型資料夾

### Q: 無法認證怎麼辦？
A:
1. 檢查網路連接
2. 確認已啟用 Google Drive API
3. 檢查 `credentials.json` 檔案格式
4. 嘗試不同認證方式（ADC → OAuth）

### Q: 下載速度很慢？
A:
1. 檢查網路連接速度
2. 降低並發下載數
3. 避免在尖峰時段下載
4. 考慮使用 Google Takeout 進行大量備份

### Q: 可以下載他人分享的檔案嗎？
A: 可以，但需要有檔案的檢視權限。建議請分享者將檔案設為「知道連結的人都能檢視」。

### Q: 支援哪些檔案類型？
A: 支援所有 Google Drive 中的檔案類型，包括：
- Google Workspace 檔案（自動轉換）
- Office 檔案（原格式下載）
- PDF、圖片、影片等（原格式下載）

## 📚 替代方案

如果本工具不符合您的需求，推薦以下替代方案：

### 🌟 Google Takeout（強烈推薦）
- **優點**：官方工具、100% 可靠、零設定
- **缺點**：無法選擇特定檔案、需等待處理
- **適用**：完整備份 Google 帳戶資料
- **連結**：https://takeout.google.com/

### 🌟 rclone（專業推薦）
- **優點**：功能強大、支援多種雲端服務、同步功能
- **缺點**：設定較複雜、需學習命令行
- **適用**：定期同步、專業用途
- **連結**：https://rclone.org/

### 📱 Google Drive 桌面版
- **優點**：官方工具、自動同步
- **缺點**：佔用本地空間、同步所有檔案
- **適用**：日常工作同步

## 🤝 貢獻和支援

### 📖 完整文件
詳細的使用指南和開發文件請參閱 **[文件中心](docs/README.md)**。

### 🐛 問題回報
如果發現 Bug 或有功能建議，請在 GitHub Issues 中回報。

### 💡 功能建議
歡迎提出新功能建議或改進意見。詳見 **[貢獻指南](docs/development/contributing.md)**。

### 📄 授權條款
本專案採用 MIT 授權條款，詳見 `LICENSE` 檔案。

## 🎉 更新日誌

### v2.0.0 (最新)
- 🆕 **新增 Office 格式自動轉換功能**
- 🆕 Google 文件 → Word (.docx)
- 🆕 Google 試算表 → Excel (.xlsx)
- 🆕 Google 簡報 → PowerPoint (.pptx)
- 🔧 改進網路重試機制
- 🔧 優化大型資料夾處理
- 🔧 增強錯誤處理和使用者體驗

### v1.0.0
- ✅ 基本下載功能
- ✅ Streamlit Web 介面
- ✅ OAuth 認證支援
- ✅ 多格式匯出

---

**🎯 立即開始使用：**
```bash
# 一鍵啟動
quick_backup.bat

# 或命令行
python simple_backup.py
```

**💡 記住：現在下載的 Google 文件將自動轉換為 Word、Excel、PowerPoint 格式，讓您立即可以使用！** 🚀 