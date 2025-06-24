# 🤝 貢獻指南

感謝您對 Google Drive 下載工具的興趣！我們歡迎各種形式的貢獻。

## 🎯 如何貢獻

### 🐛 回報 Bug
1. 檢查是否已有相同的 Issue
2. 使用 Bug 回報模板
3. 提供詳細的重現步驟
4. 包含系統環境資訊

### 💡 功能建議
1. 在 Issues 中描述功能需求
2. 說明使用場景和價值
3. 提供實作建議（如果有的話）

### 🔧 程式碼貢獻
1. Fork 專案
2. 創建功能分支：`git checkout -b feature/amazing-feature`
3. 提交變更：`git commit -m 'Add amazing feature'`
4. 推送分支：`git push origin feature/amazing-feature`
5. 開啟 Pull Request

## 📋 開發環境設置

```bash
# 1. 克隆專案
git clone https://github.com/your-username/google_drive_download.git
cd google_drive_download

# 2. 創建虛擬環境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 3. 安裝依賴
pip install -r requirements.txt

# 4. 運行測試
python -m pytest tests/

# 5. 啟動開發服務
python run_streamlit.py
```

## 🎨 程式碼風格

- 使用 Black 進行程式碼格式化
- 遵循 PEP 8 規範
- 添加適當的註釋和文檔字串
- 保持函數簡潔，單一職責

## 📝 提交訊息格式

```
<type>(<scope>): <description>

<body>

<footer>
```

**類型：**
- `feat`: 新功能
- `fix`: Bug 修復
- `docs`: 文檔更新
- `style`: 格式化
- `refactor`: 重構
- `test`: 測試相關
- `chore`: 雜項任務

**範例：**
```
feat(converter): 添加 PowerPoint 轉換支援

- 新增 Google Slides 到 PPTX 格式轉換
- 改進轉換錯誤處理
- 更新相關測試

Closes #123
```

## 🧪 測試

- 為新功能編寫測試
- 確保所有測試通過
- 測試覆蓋率應保持在 80% 以上

## 📚 文檔

- 更新 README.md（如果需要）
- 添加功能說明
- 更新 API 文檔

## 🏆 貢獻者

感謝所有貢獻者！您的名字將出現在這裡。

## 📞 聯繫我們

- GitHub Issues：回報問題和建議
- Email：[您的聯絡信箱]
- Discord：[社群連結]

---

**歡迎加入我們，一起讓這個工具變得更好！** 🚀 