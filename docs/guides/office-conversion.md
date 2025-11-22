# 🔄 Google Drive Office 格式自動轉換功能

## ✨ 功能簡介

本工具現在支援**自動將 Google Workspace 文件轉換為 Microsoft Office 格式**，讓您下載後可以直接使用 Word、Excel、PowerPoint 等軟體開啟。

## 🎯 轉換對應表

| Google Workspace 文件類型 | 自動轉換為 | 檔案格式 |
|-------------------------|-----------|---------|
| 📝 Google 文件 (Docs) | Microsoft Word | `.docx` |
| 📊 Google 試算表 (Sheets) | Microsoft Excel | `.xlsx` |
| 📽️ Google 簡報 (Slides) | Microsoft PowerPoint | `.pptx` |
| 🎨 Google 繪圖 (Drawings) | PNG 圖片 | `.png` |
| 📋 Google 表單 (Forms) | 表單資料 | `.zip` |

## 🚀 如何使用

### 方法一：簡化版命令行工具
```bash
python simple_backup.py
```

執行後會詢問：
```
是否轉換為 Office 格式？(Y/n):
```
- 直接按 Enter 或輸入 `y` → **自動轉換為 Office 格式**
- 輸入 `n` → 保持原格式或使用其他格式

### 方法二：Streamlit Web 介面
```bash
python run_streamlit.py
```

在下載設定中會看到：
- ✅ **自動轉換為 Office 格式** (預設勾選)
- 顯示：`將自動轉換：Google文件→Word (.docx)、試算表→Excel (.xlsx)、簡報→PowerPoint (.pptx)`

## 📋 轉換示例

### 下載前
```
📂 我的專案資料夾/
├── 📝 專案提案書 (Google 文件)
├── 📊 預算表 (Google 試算表)  
├── 📽️ 簡報檔 (Google 簡報)
└── 📄 其他檔案.pdf
```

### 下載後 (開啟 Office 轉換)
```
📁 downloaded_files/
├── 📄 專案提案書.docx     ← 可用 Word 開啟
├── 📄 預算表.xlsx         ← 可用 Excel 開啟
├── 📄 簡報檔.pptx         ← 可用 PowerPoint 開啟
└── 📄 其他檔案.pdf        ← 原格式保持不變
```

## 🔧 進階設定

### 自訂格式轉換
如果您想要特定格式，可以手動選擇：

**Streamlit 介面：**
- 取消勾選 "自動轉換為 Office 格式"
- 從下拉選單選擇：`pdf`, `docx`, `xlsx`, `pptx`, `txt`, `html`

**命令行：**
- 輸入 `n` 不使用自動轉換
- 程式將詢問您偏好的格式

### 格式優先級
系統選擇格式的順序：
1. **使用者指定格式** (如果有)
2. **預設 Office 格式** (如果是 Google Workspace 檔案)
3. **第一個可用格式** (最後選擇)

## ⚠️ 注意事項

### 支援的檔案類型
- ✅ **Google 文件、試算表、簡報**：完整支援轉換
- ✅ **Google 繪圖**：轉換為 PNG 圖片
- ✅ **Google 表單**：匯出為 ZIP 檔案
- ❌ **一般檔案** (PDF、圖片、影片等)：保持原格式

### 檔案相容性
- **Word 文件 (.docx)**：與 Microsoft Word 2007+ 相容
- **Excel 試算表 (.xlsx)**：與 Microsoft Excel 2007+ 相容
- **PowerPoint 簡報 (.pptx)**：與 Microsoft PowerPoint 2007+ 相容
- **替代軟體**：也可使用 LibreOffice、WPS Office 等開啟

### 檔案大小限制
- Google Drive API 有檔案大小限制
- 大型檔案可能需要較長轉換時間
- 建議單次下載不超過 1GB

## 🆘 常見問題

**Q: 為什麼有些檔案沒有轉換？**
A: 只有 Google Workspace 檔案會被轉換，一般檔案 (如 PDF、圖片) 保持原格式。

**Q: 可以選擇只轉換特定類型的檔案嗎？**
A: 目前不支援，但您可以關閉自動轉換，手動選擇格式。

**Q: 轉換後的檔案能完全還原原始格式嗎？**
A: Office 格式轉換可能會有些微差異，但大部分內容和格式都會保留。

**Q: 下載速度會變慢嗎？**
A: 轉換過程在 Google 伺服器進行，對下載速度影響微小。

## 🎉 使用建議

1. **一般用途**：建議開啟 Office 格式轉換，便於日常編輯使用
2. **備份用途**：如需完整保存原始格式，可選擇 PDF 格式
3. **分享用途**：Office 格式相容性更好，適合跨平台分享
4. **大量下載**：啟用自動轉換可省去後續手動轉換的麻煩

---

**💡 提示：** 這個功能讓您的 Google Drive 檔案下載後立即可用，無需額外的格式轉換步驟！ 