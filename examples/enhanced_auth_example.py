"""
增強認證系統使用示例
展示統一工廠模式、安全儲存和重試機制的使用方法
"""

import os
import sys
import time
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.enhanced_auth_manager import enhanced_auth_manager, quick_enhanced_auth
from src.core.auth_factory import AuthFactory, AuthType, get_auth_status
from src.core.secure_token_storage import secure_token_storage
from src.core.retry_manager import retry, RetryStrategy
from src.utils.logger import get_logger

logger = get_logger(__name__)


def demo_factory_pattern():
    """示範認證工廠模式的使用"""
    print("\n" + "="*50)
    print("🏭 認證工廠模式示範")
    print("="*50)
    
    # 取得可用的認證類型
    available_types = AuthFactory.get_available_auth_types()
    print(f"可用的認證類型: {available_types}")
    
    # 自動偵測可用的認證
    auto_auth = AuthFactory.auto_detect_auth()
    if auto_auth:
        print(f"自動偵測到認證類型: {type(auto_auth).__name__}")
    else:
        print("未偵測到可用的認證")
    
    # 手動建立特定類型的認證
    try:
        adc_auth = AuthFactory.create_auth(AuthType.ADC.value)
        print(f"建立 ADC 認證實例: {adc_auth}")
    except Exception as e:
        print(f"建立 ADC 認證失敗: {e}")


def demo_secure_storage():
    """示範安全令牌儲存的使用"""
    print("\n" + "="*50)
    print("🔐 安全令牌儲存示範")
    print("="*50)
    
    # 查看現有令牌
    tokens = secure_token_storage.list_tokens()
    print(f"現有令牌數量: {len(tokens)}")
    
    for token_id, metadata in tokens.items():
        print(f"  {token_id}: {metadata['auth_type']} - {metadata['identifier']}")
    
    # 清理過期令牌
    cleaned = secure_token_storage.cleanup_expired_tokens()
    print(f"清理過期令牌: {cleaned} 個")
    
    # 顯示儲存狀態
    print(f"加密功能: {'啟用' if secure_token_storage.enable_encryption else '停用'}")
    print(f"儲存目錄: {secure_token_storage.storage_dir}")


@retry(max_retries=2, strategy=RetryStrategy.EXPONENTIAL)
def demo_retry_mechanism():
    """示範重試機制的使用"""
    print("\n" + "="*50)
    print("🔄 重試機制示範")
    print("="*50)
    
    # 模擬可能失敗的操作
    import random
    
    if random.random() < 0.7:  # 70% 機率失敗
        print("模擬操作失敗...")
        raise Exception("模擬的網路錯誤")
    else:
        print("操作成功!")
        return "成功結果"


def demo_enhanced_auth_manager():
    """示範增強認證管理器的使用"""
    print("\n" + "="*50)
    print("⚡ 增強認證管理器示範")
    print("="*50)
    
    # 取得認證狀態
    status = enhanced_auth_manager.get_auth_status()
    print("認證狀態:")
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    # 嘗試認證
    try:
        result = enhanced_auth_manager.authenticate()
        if result.success:
            print(f"✅ 認證成功: {result.message}")
            
            # 取得 Drive 服務
            try:
                drive_service = enhanced_auth_manager.get_drive_service()
                print(f"Drive 服務已就緒: {type(drive_service).__name__}")
                
                # 簡單測試 API 呼叫
                about = drive_service.about().get(fields="user").execute()
                user_email = about.get('user', {}).get('emailAddress', 'Unknown')
                print(f"目前使用者: {user_email}")
                
            except Exception as e:
                print(f"取得 Drive 服務失敗: {e}")
                
        else:
            print(f"❌ 認證失敗: {result.message}")
            
    except Exception as e:
        print(f"認證過程發生異常: {e}")
    
    # 顯示認證歷史
    history = enhanced_auth_manager.get_auth_history(limit=5)
    print(f"\n認證歷史 (最近 5 次):")
    for i, record in enumerate(history, 1):
        status_icon = "✅" if record['success'] else "❌"
        print(f"  {i}. {status_icon} {record['timestamp'].strftime('%H:%M:%S')} - {record['message']}")


def demo_quick_auth():
    """示範快速認證的使用"""
    print("\n" + "="*50)
    print("🚀 快速認證示範")
    print("="*50)
    
    try:
        # 使用快速認證
        auth_instance = quick_enhanced_auth()
        print(f"快速認證成功: {type(auth_instance).__name__}")
        
        # 取得認證資訊
        auth_info = auth_instance.get_auth_info()
        print("認證資訊:")
        for key, value in auth_info.items():
            print(f"  {key}: {value}")
            
    except Exception as e:
        print(f"快速認證失敗: {e}")


def demo_auth_status_monitoring():
    """示範認證狀態監控"""
    print("\n" + "="*50)
    print("📊 認證狀態監控示範")
    print("="*50)
    
    # 取得全域認證狀態
    global_status = get_auth_status()
    print("全域認證狀態:")
    for key, value in global_status.items():
        print(f"  {key}: {value}")
    
    # 監控循環示例（簡化版）
    print("\n開始 3 秒監控...")
    for i in range(3):
        is_auth = enhanced_auth_manager.is_authenticated()
        current_auth = enhanced_auth_manager.get_current_auth()
        auth_type = type(current_auth).__name__ if current_auth else "None"
        
        print(f"  第 {i+1} 秒: 認證狀態={is_auth}, 類型={auth_type}")
        time.sleep(1)


def main():
    """主函數"""
    print("🎯 增強認證系統完整示範")
    print("="*60)
    
    try:
        # 執行各種示範
        demo_factory_pattern()
        demo_secure_storage()
        
        # 重試機制示範
        try:
            result = demo_retry_mechanism()
            print(f"重試操作結果: {result}")
        except Exception as e:
            print(f"重試操作最終失敗: {e}")
        
        demo_enhanced_auth_manager()
        demo_quick_auth()
        demo_auth_status_monitoring()
        
        print("\n" + "="*60)
        print("✅ 所有示範完成！")
        
    except Exception as e:
        print(f"\n❌ 示範過程發生錯誤: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理
        print("\n🧹 清理資源...")
        enhanced_auth_manager.logout()


if __name__ == "__main__":
    main() 