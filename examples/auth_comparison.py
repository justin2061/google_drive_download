"""
ADC vs Service Account 比較範例
演示兩者的差異和使用場景
"""

import os
from google.auth import default
from google.oauth2 import service_account
from googleapiclient.discovery import build


def demo_service_account_direct():
    """
    方式 1: 直接使用 Service Account
    - 明確指定服務帳戶檔案
    - 直接載入服務帳戶憑證
    """
    print("=== 直接使用 Service Account ===")
    
    # 直接載入服務帳戶憑證
    credentials = service_account.Credentials.from_service_account_file(
        'service_account.json',
        scopes=['https://www.googleapis.com/auth/drive.readonly']
    )
    
    # 建立服務
    drive = build('drive', 'v3', credentials=credentials)
    
    # 取得帳戶資訊
    about = drive.about().get(fields="user").execute()
    user_email = about.get('user', {}).get('emailAddress')
    
    print(f"✅ 認證成功 - 帳戶類型: Service Account")
    print(f"📧 Email: {user_email}")
    print(f"🔧 方法: 直接載入 service_account.json")
    print()


def demo_adc_with_service_account():
    """
    方式 2: 透過 ADC 使用 Service Account
    - 設定環境變數 GOOGLE_APPLICATION_CREDENTIALS
    - ADC 自動偵測並使用服務帳戶
    """
    print("=== 透過 ADC 使用 Service Account ===")
    
    # 設定環境變數（在實際使用中應該在外部設定）
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'service_account.json'
    
    # ADC 自動偵測認證
    credentials, project = default(scopes=['https://www.googleapis.com/auth/drive.readonly'])
    
    # 建立服務
    drive = build('drive', 'v3', credentials=credentials)
    
    # 取得帳戶資訊
    about = drive.about().get(fields="user").execute()
    user_email = about.get('user', {}).get('emailAddress')
    
    print(f"✅ 認證成功 - 帳戶類型: Service Account (透過 ADC)")
    print(f"📧 Email: {user_email}")
    print(f"🔧 方法: ADC 自動偵測環境變數")
    print(f"📁 專案 ID: {project}")
    print()


def demo_adc_with_user_credentials():
    """
    方式 3: 透過 ADC 使用使用者認證
    - 使用 gcloud auth application-default login
    - ADC 自動使用使用者的個人帳戶
    """
    print("=== 透過 ADC 使用使用者認證 ===")
    
    # 清除服務帳戶環境變數
    if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
        del os.environ['GOOGLE_APPLICATION_CREDENTIALS']
    
    try:
        # ADC 自動偵測使用者認證
        credentials, project = default(scopes=['https://www.googleapis.com/auth/drive.readonly'])
        
        # 建立服務
        drive = build('drive', 'v3', credentials=credentials)
        
        # 取得帳戶資訊
        about = drive.about().get(fields="user").execute()
        user_email = about.get('user', {}).get('emailAddress')
        
        print(f"✅ 認證成功 - 帳戶類型: User Account (透過 ADC)")
        print(f"📧 Email: {user_email}")
        print(f"🔧 方法: ADC 使用 gcloud 使用者認證")
        print(f"📁 專案 ID: {project}")
        
    except Exception as e:
        print(f"❌ 使用者認證不可用: {e}")
        print("💡 請執行: gcloud auth application-default login")
    
    print()


def show_adc_priority_order():
    """
    展示 ADC 的優先順序
    """
    print("=== ADC 認證來源優先順序 ===")
    
    priorities = [
        "1. GOOGLE_APPLICATION_CREDENTIALS 環境變數",
        "2. gcloud auth application-default login 使用者認證", 
        "3. Google Cloud 環境 metadata service",
        "4. Google Cloud SDK 預設專案的服務帳戶"
    ]
    
    for priority in priorities:
        print(f"📋 {priority}")
    
    print()
    print("🔍 ADC 會按照順序檢查這些來源，使用第一個可用的認證")
    print()


def main():
    """
    主函數 - 執行所有範例
    """
    print("🔐 Google Drive 認證方式比較\n")
    
    show_adc_priority_order()
    
    try:
        demo_service_account_direct()
    except Exception as e:
        print(f"❌ Service Account 直接認證失敗: {e}\n")
    
    try:
        demo_adc_with_service_account()
    except Exception as e:
        print(f"❌ ADC + Service Account 認證失敗: {e}\n")
    
    try:
        demo_adc_with_user_credentials()
    except Exception as e:
        print(f"❌ ADC + User Credentials 認證失敗: {e}\n")
    
    print("=== 總結 ===")
    print("🎯 Service Account: 特定的帳戶類型")
    print("🎯 ADC: 自動偵測認證的機制")
    print("🎯 ADC 可以使用 Service Account，但不限於此")
    print("🎯 選擇認證方式應根據使用場景決定")


if __name__ == "__main__":
    main() 