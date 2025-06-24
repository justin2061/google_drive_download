#!/usr/bin/env python3
"""
簡化版 Google Drive 備份工具
直接下載檔案，無複雜的 UI 和狀態管理
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# 添加專案根目錄到路徑
sys.path.append(str(Path(__file__).parent))

from src.core.auth import AuthManager
from src.core.file_handler import FileHandler
from src.utils.logger import setup_logging, get_logger
from src.utils.helpers import extract_file_id_from_url, format_bytes

# 設定日誌
setup_logging()
logger = get_logger(__name__)


class SimpleBackup:
    """簡化版備份工具"""
    
    def __init__(self):
        self.auth_manager = AuthManager()
        self.file_handler = FileHandler()
        
    def authenticate(self):
        """簡單認證"""
        print("🔐 正在認證...")
        success = self.auth_manager.authenticate()
        if success:
            user_info = self.auth_manager.get_user_info()
            print(f"✅ 認證成功！歡迎 {user_info.get('email', 'Unknown')}")
            return True
        else:
            print("❌ 認證失敗")
            return False
    
    def download_folder_simple(self, folder_url_or_id: str, output_dir: str = None, office_format: bool = True):
        """簡單下載資料夾
        
        Args:
            folder_url_or_id: 資料夾 URL 或 ID
            output_dir: 輸出目錄
            office_format: 是否轉換為 Office 格式
        """
        # 提取檔案 ID
        file_id = extract_file_id_from_url(folder_url_or_id)
        if not file_id:
            file_id = folder_url_or_id
        
        # 設定輸出目錄
        if not output_dir:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = f"backup_{timestamp}"
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        try:
            print(f"📁 正在分析資料夾...")
            
            # 取得資料夾資訊
            folder_info = self.file_handler.get_file_info(file_id)
            folder_name = folder_info.get('name', 'Unknown')
            print(f"📂 資料夾名稱: {folder_name}")
            
            # 取得檔案清單（限制深度避免卡住）
            print("🔍 正在取得檔案清單...")
            files = self.file_handler.get_folder_contents(file_id, recursive=True, max_depth=3)
            
            # 篩選出實際的檔案（非資料夾）
            actual_files = [f for f in files if f.get('mimeType') != 'application/vnd.google-apps.folder']
            
            print(f"📄 找到 {len(actual_files)} 個檔案")
            
            if not actual_files:
                print("⚠️ 沒有找到可下載的檔案")
                return
            
            # 分析檔案類型
            google_workspace_files = []
            regular_files = []
            
            for file_info in actual_files:
                mime_type = file_info.get('mimeType', '')
                if mime_type.startswith('application/vnd.google-apps.'):
                    google_workspace_files.append(file_info)
                else:
                    regular_files.append(file_info)
            
            # 顯示檔案統計和轉換資訊
            print(f"\n📊 檔案分析:")
            print(f"📝 Google Workspace 檔案: {len(google_workspace_files)} 個")
            print(f"📄 一般檔案: {len(regular_files)} 個")
            
            if google_workspace_files and office_format:
                print(f"\n🔄 將自動轉換為 Office 格式:")
                conversion_info = {}
                for file_info in google_workspace_files:
                    mime_type = file_info.get('mimeType')
                    office_name = self.file_handler.converter.get_office_format_name(mime_type)
                    if office_name not in conversion_info:
                        conversion_info[office_name] = 0
                    conversion_info[office_name] += 1
                
                for format_name, count in conversion_info.items():
                    print(f"   → {count} 個檔案將轉為 {format_name}")
            
            # 計算總大小
            total_size = sum(int(f.get('size', 0)) for f in actual_files if f.get('size'))
            print(f"💾 總大小: {format_bytes(total_size)}")
            
            # 確認下載
            format_note = " (自動轉換為 Office 格式)" if office_format and google_workspace_files else ""
            response = input(f"\n是否要下載這 {len(actual_files)} 個檔案到 '{output_path}'{format_note}？ (y/N): ")
            if response.lower() != 'y':
                print("❌ 取消下載")
                return
            
            # 開始下載
            print(f"\n🚀 開始下載到 {output_path}")
            downloaded_count = 0
            failed_count = 0
            converted_count = 0
            
            for i, file_info in enumerate(actual_files, 1):
                file_name = file_info.get('name', 'unknown')
                file_id = file_info.get('id')
                mime_type = file_info.get('mimeType', '')
                
                print(f"[{i}/{len(actual_files)}] 📥 {file_name}")
                
                try:
                    # 決定使用的格式
                    preferred_format = None
                    if office_format and mime_type.startswith('application/vnd.google-apps.'):
                        # 使用預設的 Office 格式（在 get_export_format 中自動選擇）
                        office_name = self.file_handler.converter.get_office_format_name(mime_type)
                        print(f"    🔄 轉換為 {office_name}")
                        converted_count += 1
                    
                    # 下載檔案內容
                    content = self.file_handler.download_file_content(file_id, preferred_format=preferred_format)
                    
                    # 生成檔案名稱
                    safe_filename = self.file_handler.generate_safe_filename(file_info, preferred_format)
                    file_path = output_path / safe_filename
                    
                    # 儲存檔案
                    self.file_handler.save_file(content, file_path, file_info)
                    
                    downloaded_count += 1
                    print(f"    ✅ 完成 ({format_bytes(len(content))})")
                    
                except Exception as e:
                    failed_count += 1
                    print(f"    ❌ 失敗: {e}")
                    logger.error(f"下載失敗 {file_name}: {e}")
            
            # 下載結果
            print(f"\n📊 下載完成!")
            print(f"✅ 成功: {downloaded_count} 個檔案")
            if converted_count > 0:
                print(f"🔄 轉換: {converted_count} 個 Google Workspace 檔案")
            print(f"❌ 失敗: {failed_count} 個檔案")
            print(f"📁 儲存位置: {output_path.absolute()}")
            
        except Exception as e:
            print(f"❌ 下載過程發生錯誤: {e}")
            logger.error(f"下載過程錯誤: {e}")
    
    def download_single_file(self, file_url_or_id: str, output_dir: str = None, office_format: bool = True):
        """下載單一檔案"""
        file_id = extract_file_id_from_url(file_url_or_id)
        if not file_id:
            file_id = file_url_or_id
        
        if not output_dir:
            output_dir = "downloads"
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        try:
            print("📄 正在取得檔案資訊...")
            file_info = self.file_handler.get_file_info(file_id)
            file_name = file_info.get('name', 'unknown')
            file_size = file_info.get('size', '0')
            mime_type = file_info.get('mimeType', '')
            
            print(f"📝 檔案名稱: {file_name}")
            print(f"💾 檔案大小: {format_bytes(int(file_size)) if file_size.isdigit() else 'Unknown'}")
            
            # 檢查是否為 Google Workspace 檔案
            is_google_workspace = mime_type.startswith('application/vnd.google-apps.')
            if is_google_workspace and office_format:
                office_name = self.file_handler.converter.get_office_format_name(mime_type)
                print(f"🔄 將轉換為: {office_name}")
            
            # 下載檔案
            print("📥 正在下載...")
            preferred_format = None if not office_format else None  # 使用預設 Office 格式
            content = self.file_handler.download_file_content(file_id, preferred_format=preferred_format)
            
            # 儲存檔案
            safe_filename = self.file_handler.generate_safe_filename(file_info, preferred_format)
            file_path = output_path / safe_filename
            self.file_handler.save_file(content, file_path, file_info)
            
            print(f"✅ 下載完成!")
            if is_google_workspace and office_format:
                print(f"🔄 已自動轉換為 Office 格式")
            print(f"📁 儲存位置: {file_path.absolute()}")
            
        except Exception as e:
            print(f"❌ 下載失敗: {e}")
            logger.error(f"單檔下載錯誤: {e}")


def main():
    """主函數"""
    backup = SimpleBackup()
    
    print("🚀 簡化版 Google Drive 備份工具")
    print("=" * 50)
    print("🆕 新功能：自動轉換為 Office 格式")
    print("   📝 Google文件 → Word (.docx)")
    print("   📊 Google試算表 → Excel (.xlsx)")  
    print("   📽️ Google簡報 → PowerPoint (.pptx)")
    print("=" * 50)
    
    # 認證
    if not backup.authenticate():
        return
    
    while True:
        print("\n選擇操作:")
        print("1. 📁 下載整個資料夾")
        print("2. 📄 下載單一檔案")
        print("3. 🚪 退出")
        
        choice = input("\n請選擇 (1-3): ").strip()
        
        if choice == '1':
            url = input("請輸入資料夾 URL 或 ID: ").strip()
            if url:
                output = input("輸出目錄 (留空使用預設): ").strip() or None
                office_format_input = input("是否轉換為 Office 格式？(Y/n): ").strip().lower()
                office_format = office_format_input != 'n'  # 預設為 True，除非輸入 'n'
                backup.download_folder_simple(url, output, office_format)
        
        elif choice == '2':
            url = input("請輸入檔案 URL 或 ID: ").strip()
            if url:
                output = input("輸出目錄 (留空使用 'downloads'): ").strip() or None
                office_format_input = input("是否轉換為 Office 格式？(Y/n): ").strip().lower()
                office_format = office_format_input != 'n'  # 預設為 True，除非輸入 'n'
                backup.download_single_file(url, output, office_format)
        
        elif choice == '3':
            print("👋 再見!")
            break
        
        else:
            print("❌ 無效的選擇")


if __name__ == "__main__":
    main() 