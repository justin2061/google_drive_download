#!/usr/bin/env python3
"""
ADC (Application Default Credentials) 設定助手
幫助用戶正確設定 Google Cloud 認證
"""

import os
import subprocess
import sys
from pathlib import Path


def check_gcloud_installed():
    """檢查是否已安裝 gcloud CLI"""
    try:
        result = subprocess.run(['gcloud', 'version'], 
                              capture_output=True, text=True, check=True)
        print("✅ Google Cloud SDK 已安裝")
        print(f"版本資訊:\n{result.stdout}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Google Cloud SDK 未安裝")
        return False


def check_current_auth():
    """檢查當前認證狀態"""
    try:
        result = subprocess.run(['gcloud', 'auth', 'list'], 
                              capture_output=True, text=True, check=True)
        print("📋 當前認證帳戶:")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 檢查認證狀態失敗: {e}")
        return False


def check_application_default_credentials():
    """檢查 Application Default Credentials 狀態"""
    try:
        result = subprocess.run(['gcloud', 'auth', 'application-default', 'print-access-token'], 
                              capture_output=True, text=True, check=True)
        print("✅ Application Default Credentials 已設定")
        return True
    except subprocess.CalledProcessError:
        print("❌ Application Default Credentials 未設定")
        return False


def check_environment_variable():
    """檢查 GOOGLE_APPLICATION_CREDENTIALS 環境變數"""
    creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if creds_path:
        if Path(creds_path).exists():
            print(f"✅ GOOGLE_APPLICATION_CREDENTIALS 已設定: {creds_path}")
            return True
        else:
            print(f"⚠️ GOOGLE_APPLICATION_CREDENTIALS 設定的檔案不存在: {creds_path}")
            return False
    else:
        print("ℹ️ GOOGLE_APPLICATION_CREDENTIALS 環境變數未設定")
        return False


def setup_application_default_login():
    """設定 Application Default Credentials"""
    print("\n🔧 設定 Application Default Credentials...")
    print("這將開啟瀏覽器進行 Google 帳戶授權")
    
    confirm = input("是否繼續? (y/N): ").lower().strip()
    if confirm != 'y':
        print("取消設定")
        return False
    
    try:
        subprocess.run(['gcloud', 'auth', 'application-default', 'login'], check=True)
        print("✅ Application Default Credentials 設定成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 設定失敗: {e}")
        return False


def show_adc_priority():
    """顯示 ADC 認證優先順序"""
    print("\n📋 ADC 認證來源優先順序:")
    priorities = [
        "1. GOOGLE_APPLICATION_CREDENTIALS 環境變數",
        "2. gcloud auth application-default login 使用者認證", 
        "3. Google Cloud 環境 metadata service",
        "4. Google Cloud SDK 預設專案的服務帳戶"
    ]
    
    for priority in priorities:
        print(f"   {priority}")
    
    print("\n💡 ADC 會按順序檢查這些來源，使用第一個可用的認證")


def show_setup_guide():
    """顯示設定指南"""
    print("\n📖 ADC 設定指南:")
    print("\n方法 1: 使用個人帳戶 (推薦用於開發)")
    print("   gcloud auth application-default login")
    
    print("\n方法 2: 使用服務帳戶")
    print("   1. 在 Google Cloud Console 建立服務帳戶")
    print("   2. 下載服務帳戶 JSON 檔案")
    print("   3. 設定環境變數:")
    print("      export GOOGLE_APPLICATION_CREDENTIALS='path/to/service_account.json'")
    
    print("\n方法 3: 在 Google Cloud 環境中 (自動)")
    print("   - Compute Engine、Cloud Run、GKE 等會自動提供認證")


def main():
    """主函數"""
    print("🔐 ADC (Application Default Credentials) 設定助手\n")
    
    # 檢查 gcloud 是否安裝
    if not check_gcloud_installed():
        print("\n📥 請先安裝 Google Cloud SDK:")
        print("   https://cloud.google.com/sdk/docs/install")
        return 1
    
    print("\n" + "="*50)
    
    # 檢查各種認證狀態
    print("🔍 檢查認證狀態...\n")
    
    env_ok = check_environment_variable()
    adc_ok = check_application_default_credentials()
    
    print("\n" + "="*50)
    
    if env_ok or adc_ok:
        print("✅ ADC 認證已設定，您的應用程式應該可以正常運作")
        check_current_auth()
    else:
        print("⚠️ 需要設定 ADC 認證")
        
        show_adc_priority()
        show_setup_guide()
        
        print("\n" + "="*50)
        
        # 提供快速設定選項
        if input("\n是否要設定 Application Default Credentials? (y/N): ").lower().strip() == 'y':
            if setup_application_default_login():
                print("\n🎉 設定完成！您的應用程式現在應該可以使用 ADC 認證")
            else:
                print("\n❌ 設定失敗，請手動設定或使用其他認證方式")
                return 1
    
    print("\n💡 提示: 重新啟動您的應用程式以使用新的認證設定")
    return 0


if __name__ == "__main__":
    sys.exit(main()) 