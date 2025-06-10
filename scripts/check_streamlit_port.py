#!/usr/bin/env python3
"""
Streamlit 端口診斷工具

檢查為什麼 Streamlit 使用 8080 端口而非預設的 8501 端口
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def check_environment_variables():
    """檢查相關環境變數"""
    print("🔍 檢查環境變數...")
    
    streamlit_vars = [
        'STREAMLIT_SERVER_PORT',
        'STREAMLIT_SERVER_ADDRESS',
        'STREAMLIT_SERVER_HEADLESS',
        'SERVER_PORT',
        'PORT'
    ]
    
    found_vars = {}
    for var in streamlit_vars:
        value = os.getenv(var)
        if value:
            found_vars[var] = value
            print(f"   {var} = {value}")
    
    if not found_vars:
        print("   ✅ 未發現相關環境變數")
    
    return found_vars

def check_streamlit_config():
    """檢查 Streamlit 配置"""
    print("\n🔧 檢查 Streamlit 配置...")
    
    # 檢查可能的配置檔案位置
    config_paths = [
        Path.home() / '.streamlit' / 'config.toml',
        Path('.streamlit') / 'config.toml',
        Path('streamlit') / 'config.toml'
    ]
    
    config_found = False
    for path in config_paths:
        if path.exists():
            print(f"   📁 發現配置檔案: {path}")
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                print(f"   📄 內容:")
                print("   " + "\n   ".join(content.split('\n')[:10]))  # 只顯示前10行
                config_found = True
            except Exception as e:
                print(f"   ❌ 讀取失敗: {e}")
    
    if not config_found:
        print("   ✅ 未發現 Streamlit 配置檔案")

def check_running_processes():
    """檢查正在運行的 Streamlit 進程"""
    print("\n🔍 檢查正在運行的 Streamlit 進程...")
    
    try:
        # Windows 系統
        if os.name == 'nt':
            # 使用 netstat 檢查端口
            result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            
            streamlit_ports = []
            for line in lines:
                if ':8080' in line or ':8501' in line:
                    parts = line.split()
                    if len(parts) >= 4 and 'LISTENING' in line:
                        port = parts[1].split(':')[-1]
                        pid = parts[-1]
                        streamlit_ports.append((port, pid))
            
            if streamlit_ports:
                print("   發現監聽的端口:")
                for port, pid in streamlit_ports:
                    print(f"   📍 端口 {port} - PID {pid}")
                    
                    # 檢查進程詳情
                    try:
                        tasklist_result = subprocess.run(
                            ['tasklist', '/FI', f'PID eq {pid}'], 
                            capture_output=True, text=True
                        )
                        print(f"   📋 PID {pid}: {tasklist_result.stdout.strip().split()[-4:-1]}")
                    except:
                        pass
            else:
                print("   ✅ 未發現 Streamlit 相關端口")
        
    except Exception as e:
        print(f"   ❌ 檢查失敗: {e}")

def check_streamlit_command():
    """檢查 Streamlit 命令和參數"""
    print("\n🔍 檢查可能的 Streamlit 啟動方式...")
    
    # 常見的啟動方式
    common_commands = [
        "streamlit run ui/streamlit_app.py",
        "streamlit run ui/streamlit_app.py --server.port 8080",
        "python -m streamlit run ui/streamlit_app.py",
        "python -m streamlit run ui/streamlit_app.py --server.port 8080"
    ]
    
    print("   常見啟動方式:")
    for cmd in common_commands:
        print(f"   📝 {cmd}")
    
    # 檢查是否有啟動腳本
    script_files = ['start.py', 'run.py', 'app.py', 'main.py']
    for script in script_files:
        if Path(script).exists():
            print(f"   📄 發現啟動腳本: {script}")

def get_streamlit_default_config():
    """取得 Streamlit 預設配置"""
    print("\n⚙️ Streamlit 預設配置...")
    
    try:
        # 嘗試導入 streamlit 並檢查預設配置
        import streamlit as st
        print(f"   📦 Streamlit 版本: {st.__version__}")
        print("   📍 預設端口: 8501")
        print("   📍 預設主機: localhost")
        
    except ImportError:
        print("   ❌ 無法導入 Streamlit")

def suggest_solutions():
    """提供解決方案建議"""
    print("\n💡 解決方案建議:")
    print("=" * 50)
    
    print("1. 🔧 修改 Streamlit 啟動命令:")
    print("   streamlit run ui/streamlit_app.py --server.port 8501")
    print("   # 使用預設的 8501 端口")
    
    print("\n2. 🔄 同時修改 OAuth 配置:")
    print("   在 config.yaml 中將 auth.port 改為 8501")
    print("   並在 Google Cloud Console 中添加:")
    print("   http://localhost:8501/")
    
    print("\n3. 🎯 或者保持現狀:")
    print("   在 Google Cloud Console 中確保包含:")
    print("   http://localhost:8080/")
    print("   http://localhost:8501/")
    
    print("\n4. 🛠️ 建立 .streamlit/config.toml:")
    print("   [server]")
    print("   port = 8501")
    print("   headless = true")

def main():
    """主程式"""
    print("🔍 Streamlit 端口診斷工具")
    print("=" * 50)
    
    # 各項檢查
    check_environment_variables()
    check_streamlit_config()
    check_running_processes()
    check_streamlit_command()
    get_streamlit_default_config()
    suggest_solutions()
    
    print("\n" + "=" * 50)
    print("📊 診斷完成！")

if __name__ == "__main__":
    main() 