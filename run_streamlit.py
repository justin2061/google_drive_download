#!/usr/bin/env python3
"""
Google Drive 下載工具 - Streamlit Web 介面啟動腳本
"""

import subprocess
import sys
from pathlib import Path


def main():
    """啟動 Streamlit 應用程式"""
    
    # 確保在正確的目錄中
    project_root = Path(__file__).parent
    ui_app_path = project_root / "ui" / "streamlit_app.py"
    
    if not ui_app_path.exists():
        print(f"❌ 找不到 Streamlit 應用程式檔案: {ui_app_path}")
        sys.exit(1)
    
    print("🚀 啟動 Google Drive 下載工具 Web 介面...")
    print(f"📁 專案路徑: {project_root}")
    print(f"🌐 應用程式檔案: {ui_app_path}")
    print("-" * 50)
    
    try:
        # 啟動 Streamlit 應用程式
        cmd = [
            sys.executable, "-m", "streamlit", "run", 
            str(ui_app_path),
            "--server.port=8501",
            "--server.address=localhost",
            "--server.headless=false",
            "--browser.serverAddress=localhost",
            "--browser.gatherUsageStats=false"
        ]
        
        print("🔗 應用程式將在瀏覽器中開啟: http://localhost:8501")
        print("⏹️  按 Ctrl+C 停止服務")
        print("-" * 50)
        
        subprocess.run(cmd, cwd=project_root)
        
    except KeyboardInterrupt:
        print("\n⏹️  應用程式已停止")
    except Exception as e:
        print(f"❌ 啟動失敗: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 