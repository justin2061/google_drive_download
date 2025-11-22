# Python 打包工具規劃文件

## 📋 概述

本文檔記錄 Google Drive 下載工具的 Python 打包方案規劃，比較主流打包工具並提供實作建議。

## 🎯 打包需求分析

### **目標應用程式**
- **Streamlit Web 介面** (`ui/streamlit_app.py`)
- **CLI 命令列工具** (`src/cli/main.py`)
- **完整功能模組** (`src/` 目錄)

### **打包目標**
- ✅ 獨立可執行檔（無需 Python 環境）
- ✅ 跨平台支援（Windows、macOS、Linux）
- ✅ 包含所有依賴套件
- ✅ 使用者友善的分發方式

### **技術挑戰**
- 複雜的 Google API 依賴
- Streamlit 框架整合
- 大量第三方套件（70+ 個）
- 動態配置檔案處理

## 🔍 打包工具比較分析

### 1. **PyInstaller**

#### ✅ **優勢**
- **易用性極高**：一行命令即可打包
- **自動依賴檢測**：智慧識別 95% 以上依賴
- **Streamlit 原生支援**：內建 hooks 和最佳化
- **Google API 相容性**：完整支援 googleapis 套件
- **豐富生態**：11k+ GitHub stars，活躍社群
- **專業分發**：支援圖示、版本資訊、數位簽名

#### ❌ **劣勢**
- **檔案大小**：包含完整運行時，約 100-200MB
- **啟動速度**：單檔案模式需解壓縮（2-5秒）
- **防毒誤報**：可能被標記為可疑檔案

#### 📊 **適用場景**
- ✅ 商業應用分發
- ✅ 非技術用戶使用
- ✅ 快速原型驗證
- ✅ 複雜依賴項目

### 2. **cx_Freeze**

#### ✅ **優勢**
- **檔案精簡**：更小的打包體積（50-100MB）
- **啟動快速**：無解壓縮過程
- **跨平台一致**：統一的配置方式
- **精確控制**：細緻的依賴管理
- **純 Python**：易於客製化和除錯

#### ❌ **劣勢**
- **學習曲線**：需要撰寫 setup.py 配置
- **手動依賴**：需要明確指定複雜依賴
- **社群較小**：1.3k stars，資源相對較少
- **第三方支援**：對 Streamlit 支援較少

#### 📊 **適用場景**
- ✅ 企業內部工具
- ✅ 檔案大小敏感
- ✅ 客製化需求高
- ✅ 專業開發團隊

### 3. **其他選項**

#### **Nuitka**
- 編譯為原生機器碼
- 執行效能最佳
- 但相容性問題較多

#### **auto-py-to-exe**
- PyInstaller 的 GUI 包裝
- 適合不熟悉命令列的開發者

## 🎯 專案建議方案

### **推薦選擇：PyInstaller**

#### **選擇理由**
1. **Streamlit 最佳相容性**
2. **Google APIs 完整支援**
3. **開發效率最高**
4. **用戶體驗最佳**
5. **問題解決容易**

#### **實作策略**
分階段實作，從簡單到複雜：

**階段一：基礎打包**
```bash
# CLI 工具打包
pyinstaller --onefile src/cli/main.py --name gdrive-cli

# Streamlit 應用打包
pyinstaller --onefile ui/streamlit_app.py --name gdrive-web
```

**階段二：優化配置**
```bash
# 完整配置版本
pyinstaller --onefile --windowed \
  --add-data "config;config" \
  --add-data "ui;ui" \
  --add-data "src;src" \
  --icon="assets/icon.ico" \
  --name="GoogleDriveDownloader" \
  --version-file="version_info.txt" \
  ui/streamlit_app.py
```

**階段三：高級優化**
- 建立 `.spec` 配置檔案
- 自訂 hooks 處理特殊依賴
- 最佳化檔案大小
- 多平台自動建置

## 📝 詳細實作規劃

### **1. 環境準備**

```bash
# 安裝打包工具
pip install pyinstaller
pip install auto-py-to-exe  # 可選的 GUI 工具

# 驗證安裝
pyinstaller --version
```

### **2. CLI 工具打包**

#### **基本配置**
```bash
# 簡單打包
pyinstaller --onefile --console src/cli/main.py --name gdrive-cli

# 包含配置檔案
pyinstaller --onefile --console \
  --add-data "config;config" \
  --add-data "src;src" \
  src/cli/main.py --name gdrive-cli
```

#### **進階配置 (.spec 檔案)**
```python
# gdrive-cli.spec
a = Analysis(
    ['src/cli/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config', 'config'),
        ('src', 'src'),
    ],
    hiddenimports=[
        'google.auth',
        'google.oauth2',
        'googleapiclient',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='gdrive-cli',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

### **3. Streamlit Web 應用打包**

#### **基本配置**
```bash
# 視窗應用打包
pyinstaller --onefile --windowed \
  --add-data "ui;ui" \
  --add-data "src;src" \
  --add-data "config;config" \
  ui/streamlit_app.py --name gdrive-web
```

#### **完整配置**
```bash
# 生產環境配置
pyinstaller --onefile --windowed \
  --add-data "ui;ui" \
  --add-data "src;src" \
  --add-data "config;config" \
  --add-data "logs;logs" \
  --icon="assets/icon.ico" \
  --version-file="version_info.txt" \
  --name="GoogleDriveDownloader" \
  ui/streamlit_app.py
```

### **4. 批次建置腳本**

#### **Windows 批次檔 (build.bat)**
```batch
@echo off
echo 正在建置 Google Drive 下載工具...

echo 清理舊版本...
rmdir /s /q dist 2>nul
rmdir /s /q build 2>nul

echo 建置 CLI 工具...
pyinstaller --onefile --console ^
  --add-data "config;config" ^
  --add-data "src;src" ^
  --name "gdrive-cli" ^
  src/cli/main.py

echo 建置 Web 應用...
pyinstaller --onefile --windowed ^
  --add-data "ui;ui" ^
  --add-data "src;src" ^
  --add-data "config;config" ^
  --icon="assets/icon.ico" ^
  --name "GoogleDriveDownloader" ^
  ui/streamlit_app.py

echo 建置完成！
echo CLI 工具：dist/gdrive-cli.exe
echo Web 應用：dist/GoogleDriveDownloader.exe
pause
```

#### **Python 建置腳本 (build.py)**
```python
"""
自動化建置腳本
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

def clean_build():
    """清理舊版建置檔案"""
    dirs_to_clean = ['dist', 'build']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"已清理 {dir_name} 目錄")

def build_cli():
    """建置 CLI 工具"""
    cmd = [
        'pyinstaller', '--onefile', '--console',
        '--add-data', 'config;config',
        '--add-data', 'src;src',
        '--name', 'gdrive-cli',
        'src/cli/main.py'
    ]
    
    print("正在建置 CLI 工具...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ CLI 工具建置成功")
    else:
        print("❌ CLI 工具建置失敗")
        print(result.stderr)

def build_web():
    """建置 Web 應用"""
    cmd = [
        'pyinstaller', '--onefile', '--windowed',
        '--add-data', 'ui;ui',
        '--add-data', 'src;src', 
        '--add-data', 'config;config',
        '--name', 'GoogleDriveDownloader',
        'ui/streamlit_app.py'
    ]
    
    print("正在建置 Web 應用...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Web 應用建置成功")
    else:
        print("❌ Web 應用建置失敗")
        print(result.stderr)

def main():
    """主要建置流程"""
    print("🚀 開始建置 Google Drive 下載工具")
    
    # 檢查 PyInstaller
    try:
        subprocess.run(['pyinstaller', '--version'], 
                      capture_output=True, check=True)
    except subprocess.CalledProcessError:
        print("❌ 請先安裝 PyInstaller: pip install pyinstaller")
        sys.exit(1)
    
    # 清理並建置
    clean_build()
    build_cli()
    build_web()
    
    print("\n🎉 建置完成！")
    print("📁 檔案位置：")
    print("   CLI 工具：dist/gdrive-cli.exe")
    print("   Web 應用：dist/GoogleDriveDownloader.exe")

if __name__ == "__main__":
    main()
```

## 🔧 最佳化技巧

### **1. 減少檔案大小**

```bash
# 排除不必要的模組
--exclude-module tkinter
--exclude-module matplotlib
--exclude-module PIL

# 使用 UPX 壓縮
--upx-dir /path/to/upx
```

### **2. 提升啟動速度**

```bash
# 使用目錄模式而非單檔案
pyinstaller --onedir ui/streamlit_app.py

# 優化 import
--optimize 2
```

### **3. 隱藏依賴處理**

```python
# 在 .spec 檔案中添加
hiddenimports=[
    'google.auth.transport.requests',
    'google.oauth2.credentials',
    'streamlit.web.cli',
    'streamlit.runtime.scriptrunner',
]
```

## 📊 預期結果

### **檔案大小預估**
- **CLI 工具**：50-80 MB
- **Web 應用**：100-150 MB
- **完整套件**：150-200 MB

### **效能預估**
- **啟動時間**：2-5 秒（單檔案模式）
- **記憶體使用**：50-100 MB
- **運行效能**：接近原生 Python

### **相容性**
- **Windows**：7/8/10/11 (x64)
- **macOS**：10.12+ (Intel/Apple Silicon)
- **Linux**：Ubuntu 18.04+ (x64)

## 🚀 未來擴展計劃

### **短期目標（1-3 個月）**
- [ ] 實作基本 CLI 打包
- [ ] 實作 Streamlit 應用打包
- [ ] 建立自動化建置腳本
- [ ] 跨平台測試

### **中期目標（3-6 個月）**
- [ ] 檔案大小最佳化
- [ ] 啟動速度優化
- [ ] 數位簽名整合
- [ ] 自動更新機制

### **長期目標（6-12 個月）**
- [ ] CI/CD 自動建置
- [ ] 多語言支援
- [ ] 插件系統
- [ ] 企業級分發

## 📚 參考資源

### **官方文檔**
- [PyInstaller 官方文檔](https://pyinstaller.org/)
- [cx_Freeze 官方文檔](https://cx-freeze.readthedocs.io/)

### **教學資源**
- [PyInstaller Tutorial](https://realpython.com/pyinstaller-python/)
- [Streamlit Deployment Guide](https://docs.streamlit.io/knowledge-base/tutorials/deploy)

### **最佳實踐**
- [Python 應用打包最佳實踐](https://packaging.python.org/)
- [跨平台分發指南](https://python-packaging-tutorial.readthedocs.io/)

---

**最後更新：** 2025-06-07  
**版本：** v1.0  
**維護者：** Google Drive 下載工具開發團隊 