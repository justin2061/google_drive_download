#!/usr/bin/env python3
"""
OAuth 重導向 URI 設定助手

此工具生成完整的重導向 URI 清單，以避免端口衝突問題
包含多個常用端口和格式，適用於 Google Cloud Console 設定

作者: AI Assistant
日期: 2025-01-10
"""

def generate_redirect_uris():
    """生成完整的重導向 URI 清單"""
    
    # 常用端口清單
    ports = [8080, 8081, 8000, 5000, 3000, 9000, 5758, 8888]
    
    # 主機名清單
    hosts = ['localhost', '127.0.0.1']
    
    uris = []
    
    print("🔗 生成 OAuth 重導向 URI 清單...")
    print("=" * 50)
    
    for host in hosts:
        for port in ports:
            # 帶斜線版本（推薦）
            uri_with_slash = f"http://{host}:{port}/"
            uris.append(uri_with_slash)
            
            # 不帶斜線版本（相容性）
            uri_without_slash = f"http://{host}:{port}"
            uris.append(uri_without_slash)
    
    return uris

def print_google_console_setup():
    """輸出 Google Cloud Console 設定指導"""
    
    uris = generate_redirect_uris()
    
    print("📝 Google Cloud Console 設定指導")
    print("=" * 50)
    print()
    print("1. 📂 打開 Google Cloud Console:")
    print("   https://console.cloud.google.com")
    print()
    print("2. 🔍 導航到認證設定:")
    print("   左側選單 > APIs & Services > Credentials")
    print()
    print("3. ✏️  編輯 OAuth 2.0 客戶端 ID:")
    print("   找到您的客戶端 ID 並點擊編輯圖示")
    print()
    print("4. 📋 在「已授權的重新導向 URI」中添加以下所有 URI:")
    print("   (複製貼上以下整個清單)")
    print()
    print("   " + "─" * 45)
    
    # 分組輸出，推薦的在前面
    recommended_uris = [uri for uri in uris if uri.endswith('/') and 'localhost' in uri]
    compatibility_uris = [uri for uri in uris if uri not in recommended_uris]
    
    print("   📌 推薦 URI (優先使用):")
    for uri in sorted(recommended_uris):
        print(f"   {uri}")
    
    print()
    print("   🔧 相容性 URI (備用):")
    for uri in sorted(compatibility_uris):
        print(f"   {uri}")
    
    print("   " + "─" * 45)
    print()
    print("5. 💾 儲存設定:")
    print("   點擊「儲存」按鈕")
    print()
    print("6. ⏰ 等待生效:")
    print("   設定變更可能需要幾分鐘才能生效")
    
    return uris

def print_troubleshooting():
    """輸出故障排除指導"""
    
    print("\n🔧 故障排除指導")
    print("=" * 50)
    
    print("\n❓ 如果仍然遇到 redirect_uri_mismatch 錯誤:")
    
    print("\n1. 📋 檢查端口占用:")
    print("   PowerShell: netstat -ano | findstr :8080")
    print("   如果被占用: taskkill /PID <PID> /F")
    
    print("\n2. 🔄 清理舊的認證:")
    print("   刪除 token.pickle 檔案強制重新認證")
    
    print("\n3. ⏰ 等待設定生效:")
    print("   Google Cloud Console 的設定變更需要幾分鐘")
    
    print("\n4. 🌐 檢查瀏覽器:")
    print("   清除瀏覽器快取和 cookies")
    print("   嘗試無痕模式")
    
    print("\n5. 🔍 驗證 URI 格式:")
    print("   確保 URI 完全一致（包括結尾斜線）")
    print("   範例: http://localhost:8080/")
    
    print("\n6. 📱 測試不同端口:")
    print("   如果 8080 持續被占用，程式會自動使用其他端口")
    print("   確保 Google Console 中包含這些端口的 URI")

def print_quick_copy_list():
    """輸出可快速複製的 URI 清單"""
    
    uris = generate_redirect_uris()
    
    print("\n📋 快速複製清單（給 Google Cloud Console）")
    print("=" * 50)
    print("複製以下所有行並貼到 Google Cloud Console:")
    print()
    
    for uri in sorted(set(uris)):  # 去重並排序
        print(uri)

def main():
    """主程式"""
    
    print("🚀 OAuth 重導向 URI 設定助手")
    print("=" * 50)
    print("此工具幫助您設定完整的重導向 URI，避免端口衝突問題")
    print()
    
    # 生成和顯示設定指導
    print_google_console_setup()
    
    # 故障排除
    print_troubleshooting()
    
    # 快速複製清單
    print_quick_copy_list()
    
    print("\n" + "=" * 50)
    print("🎯 設定完成後，您就可以避免 redirect_uri_mismatch 錯誤了！")
    print("💡 即使程式使用不同端口，也會自動匹配成功")
    print("=" * 50)

if __name__ == "__main__":
    main() 