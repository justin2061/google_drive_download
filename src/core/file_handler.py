"""
Google Drive 檔案處理器
提供檔案清單、轉換和管理功能
"""

import io
import ssl
import time
from typing import List, Dict, Any, Optional, Generator
from pathlib import Path
import mimetypes

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
import requests.exceptions

from ..utils.logger import LoggerMixin
from ..utils.helpers import (
    get_file_extension_from_mime_type,
    is_google_workspace_file,
    slugify,
    validate_file_id
)
from ..utils.exceptions import (
    FileNotFoundError,
    FilePermissionError,
    NetworkError,
    ValidationError
)
from .auth import get_authenticated_service, ensure_authenticated
from .retry_manager import RetryManager, RetryStrategy


class GoogleFileConverter(LoggerMixin):
    """Google Workspace 檔案轉換器"""
    
    # Google Workspace 檔案轉換對應表
    EXPORT_FORMATS = {
        'application/vnd.google-apps.document': {
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'pdf': 'application/pdf',
            'txt': 'text/plain',
            'html': 'text/html'
        },
        'application/vnd.google-apps.spreadsheet': {
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'csv': 'text/csv',
            'pdf': 'application/pdf',
            'html': 'text/html'
        },
        'application/vnd.google-apps.presentation': {
            'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'pdf': 'application/pdf',
            'txt': 'text/plain',
            'html': 'text/html'
        },
        'application/vnd.google-apps.drawing': {
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'pdf': 'application/pdf',
            'svg': 'image/svg+xml'
        },
        'application/vnd.google-apps.form': {
            'zip': 'application/zip'
        }
    }
    
    def __init__(self):
        self.logger.debug("Google 檔案轉換器已初始化")
    
    def get_export_format(self, mime_type: str, preferred_format: str = None) -> Optional[str]:
        """取得匯出格式
        
        Args:
            mime_type: Google Workspace 檔案的 MIME 類型
            preferred_format: 偏好的格式（如 'pdf', 'docx'）
            
        Returns:
            匯出格式的 MIME 類型
        """
        if mime_type not in self.EXPORT_FORMATS:
            return None
        
        available_formats = self.EXPORT_FORMATS[mime_type]
        
        # 如果指定了偏好格式且可用
        if preferred_format and preferred_format in available_formats:
            return available_formats[preferred_format]
        
        # 返回預設格式（第一個）
        return next(iter(available_formats.values()))
    
    def get_export_extension(self, mime_type: str, export_format: str) -> str:
        """取得匯出檔案的副檔名
        
        Args:
            mime_type: 原始 MIME 類型
            export_format: 匯出格式的 MIME 類型
            
        Returns:
            檔案副檔名
        """
        # 從匯出格式對應表中找到對應的副檔名
        if mime_type in self.EXPORT_FORMATS:
            for ext, format_mime in self.EXPORT_FORMATS[mime_type].items():
                if format_mime == export_format:
                    return f'.{ext}'
        
        # 退回到一般 MIME 類型對應
        return get_file_extension_from_mime_type(export_format)


class FileHandler(LoggerMixin):
    """Google Drive 檔案處理器
    
    提供檔案清單、下載和管理功能
    """
    
    def __init__(self, drive_service=None):
        self.drive_service = drive_service
        self.converter = GoogleFileConverter()
        
        # 初始化重試管理器
        self.retry_manager = RetryManager(
            max_retries=3,
            base_delay=1.0,
            max_delay=30.0,
            strategy=RetryStrategy.EXPONENTIAL,
            jitter=True
        )
        
        self.logger.info("檔案處理器已初始化")
    
    def _get_drive_service(self):
        """取得 Drive 服務實例"""
        if self.drive_service is None:
            self.drive_service = get_authenticated_service('drive')
        return self.drive_service
    
    def _safe_api_call(self, api_call_func, *args, **kwargs):
        """安全的 API 呼叫，帶有重試機制
        
        Args:
            api_call_func: API 呼叫函數
            *args: 函數參數
            **kwargs: 函數關鍵字參數
            
        Returns:
            API 呼叫結果
        """
        # 定義可重試的異常
        retryable_exceptions = (
            ConnectionError,
            TimeoutError,
            ssl.SSLError,
            requests.exceptions.RequestException,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.SSLError,
        )
        
        def wrapped_call():
            try:
                return api_call_func(*args, **kwargs)
            except retryable_exceptions as e:
                self.logger.warning(f"網路錯誤，將重試: {e}")
                raise
            except HttpError as e:
                # 某些 HTTP 錯誤也可以重試
                if e.resp.status in [429, 500, 502, 503, 504]:
                    self.logger.warning(f"HTTP 錯誤 {e.resp.status}，將重試: {e}")
                    raise
                else:
                    # 不可重試的 HTTP 錯誤
                    raise
        
        result = self.retry_manager.retry_sync(
            wrapped_call,
            custom_exceptions=retryable_exceptions + (HttpError,)
        )
        
        if not result.success:
            self.logger.error(f"API 呼叫失敗，已重試 {result.attempts} 次: {result.error}")
            raise result.error
        
        return result.result
    
    @ensure_authenticated
    def get_file_info(self, file_id: str) -> Dict[str, Any]:
        """取得檔案資訊
        
        Args:
            file_id: Google Drive 檔案 ID
            
        Returns:
            檔案資訊字典
        """
        if not validate_file_id(file_id):
            raise ValidationError('file_id', file_id, "無效的檔案 ID 格式")
        
        try:
            drive_service = self._get_drive_service()
            
            # 使用安全的 API 呼叫
            def api_call():
                return drive_service.files().get(
                    fileId=file_id,
                    fields='id,name,mimeType,size,createdTime,modifiedTime,parents,webViewLink'
                ).execute()
            
            file_info = self._safe_api_call(api_call)
            
            self.logger.debug(f"取得檔案資訊: {file_info.get('name')}")
            return file_info
            
        except HttpError as e:
            error_code = e.resp.status
            if error_code == 404:
                raise FileNotFoundError(file_id, "檔案不存在")
            elif error_code == 403:
                raise FilePermissionError(file_id, "沒有檔案存取權限")
            else:
                raise NetworkError(f"HTTP 錯誤: {e}", status_code=error_code, file_id=file_id)
        
        except Exception as e:
            self.logger.error(f"取得檔案資訊失敗: {e} (檔案ID: {file_id})")
            raise
    
    @ensure_authenticated
    def get_folder_contents(self, folder_id: str, recursive: bool = False, max_depth: int = 10, current_depth: int = 0) -> List[Dict[str, Any]]:
        """取得資料夾內容
        
        Args:
            folder_id: 資料夾 ID
            recursive: 是否遞迴取得子資料夾內容
            max_depth: 最大遞迴深度（防止無限遞迴）
            current_depth: 當前遞迴深度
            
        Returns:
            檔案清單
        """
        if not validate_file_id(folder_id):
            raise ValidationError('folder_id', folder_id, "無效的資料夾 ID 格式")
        
        # 檢查遞迴深度
        if current_depth > max_depth:
            self.logger.warning(f"達到最大遞迴深度 {max_depth}，停止遞迴")
            return []
        
        try:
            files = []
            drive_service = self._get_drive_service()
            
            # 檢查是否為資料夾
            folder_info = self.get_file_info(folder_id)
            if folder_info.get('mimeType') != 'application/vnd.google-apps.folder':
                raise ValidationError('folder_id', folder_id, "指定的 ID 不是資料夾")
            
            self.logger.info(f"處理資料夾: {folder_info.get('name')} (深度: {current_depth})")
            
            # 取得資料夾內容
            page_token = None
            page_count = 0
            max_pages = 100  # 最多處理 100 頁，防止無限循環
            
            while True:
                page_count += 1
                if page_count > max_pages:
                    self.logger.warning(f"達到最大頁數限制 {max_pages}，停止載入更多內容")
                    break
                
                query = f"'{folder_id}' in parents and trashed=false"
                
                # 使用安全的 API 呼叫
                def api_call():
                    return drive_service.files().list(
                        q=query,
                        pageSize=50,  # 進一步降低每次請求的數量
                        pageToken=page_token,
                        fields='nextPageToken,files(id,name,mimeType,size,createdTime,modifiedTime,parents,webViewLink)'
                    ).execute()
                
                try:
                    results = self._safe_api_call(api_call)
                except Exception as e:
                    # 如果遇到 500 錯誤等，記錄並跳過這個分頁
                    self.logger.error(f"載入分頁失敗，跳過: {e}")
                    break
                
                items = results.get('files', [])
                files.extend(items)
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
                
                # 短暫延遲，避免過快的請求
                time.sleep(0.2)
                
                # 每 10 頁給出進度日誌
                if page_count % 10 == 0:
                    self.logger.info(f"已載入 {page_count} 頁，共 {len(files)} 個項目")
            
            self.logger.info(f"取得資料夾內容: {len(files)} 個項目 (共 {page_count} 頁)")
            
            # 遞迴處理子資料夾
            if recursive and current_depth < max_depth:
                all_files = []
                folder_count = 0
                
                for file_info in files:
                    all_files.append(file_info)
                    
                    if file_info.get('mimeType') == 'application/vnd.google-apps.folder':
                        folder_count += 1
                        
                        # 限制每層最多處理的資料夾數量
                        if folder_count > 50:
                            self.logger.warning(f"達到單層資料夾數量限制 50，停止處理更多子資料夾")
                            break
                        
                        try:
                            # 短暫延遲，避免過快的遞迴請求
                            time.sleep(0.3)
                            self.logger.debug(f"遞迴處理子資料夾: {file_info['name']} (深度: {current_depth + 1})")
                            
                            sub_files = self.get_folder_contents(
                                file_info['id'], 
                                recursive=True, 
                                max_depth=max_depth,
                                current_depth=current_depth + 1
                            )
                            all_files.extend(sub_files)
                            
                        except Exception as e:
                            self.logger.warning(f"無法存取子資料夾 {file_info['name']}: {e} (檔案ID: {file_info['id']})")
                            # 繼續處理下一個資料夾，而不是停止整個過程
                            continue
                
                return all_files
            
            return files
            
        except HttpError as e:
            error_code = e.resp.status
            if error_code == 404:
                raise FileNotFoundError(folder_id, "資料夾不存在")
            elif error_code == 403:
                raise FilePermissionError(folder_id, "沒有資料夾存取權限")
            else:
                self.logger.error(f"HTTP 錯誤 {error_code}: {e} (資料夾ID: {folder_id})")
                # 對於 500 錯誤等，不拋出異常，而是返回空列表
                if error_code >= 500:
                    self.logger.warning(f"伺服器錯誤，返回空結果")
                    return []
                else:
                    raise NetworkError(f"HTTP 錯誤: {e}", status_code=error_code, file_id=folder_id)
        
        except Exception as e:
            self.logger.error(f"取得資料夾內容失敗: {e} (資料夾ID: {folder_id})")
            raise
    
    @ensure_authenticated
    def download_file_content(self, file_id: str, preferred_format: str = None) -> bytes:
        """下載檔案內容
        
        Args:
            file_id: 檔案 ID
            preferred_format: 偏好的匯出格式（針對 Google Workspace 檔案）
            
        Returns:
            檔案內容（位元組）
        """
        if not validate_file_id(file_id):
            raise ValidationError('file_id', file_id, "無效的檔案 ID 格式")
        
        try:
            drive_service = self._get_drive_service()
            file_info = self.get_file_info(file_id)
            
            mime_type = file_info.get('mimeType')
            
            # 處理 Google Workspace 檔案
            if is_google_workspace_file(mime_type):
                export_format = self.converter.get_export_format(mime_type, preferred_format)
                
                if not export_format:
                    raise ValidationError('mime_type', mime_type, "不支援的 Google Workspace 檔案類型")
                
                self.logger.debug(f"匯出 Google Workspace 檔案: {mime_type} -> {export_format}")
                
                request = drive_service.files().export_media(
                    fileId=file_id,
                    mimeType=export_format
                )
            else:
                # 一般檔案直接下載
                self.logger.debug(f"下載一般檔案: {mime_type}")
                
                request = drive_service.files().get_media(fileId=file_id)
            
            # 執行下載
            file_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(file_buffer, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    self.logger.debug(f"下載進度: {int(status.progress() * 100)}%")
            
            content = file_buffer.getvalue()
            self.logger.info(f"檔案下載完成: {len(content)} 位元組")
            
            return content
            
        except HttpError as e:
            error_code = e.resp.status
            if error_code == 404:
                raise FileNotFoundError(file_id, "檔案不存在")
            elif error_code == 403:
                raise FilePermissionError(file_id, "沒有檔案下載權限")
            else:
                raise NetworkError(f"HTTP 錯誤: {e}", status_code=error_code, file_id=file_id)
        
        except Exception as e:
            self.logger.error(f"下載檔案失敗: {e}")
            raise
    
    def save_file(self, file_content: bytes, file_path: Path, file_info: Dict[str, Any] = None):
        """儲存檔案到本地
        
        Args:
            file_content: 檔案內容
            file_path: 儲存路徑
            file_info: 檔案資訊（用於確定副檔名）
        """
        try:
            # 確保目錄存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 寫入檔案
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            self.logger.info(f"檔案已儲存: {file_path}")
            
        except Exception as e:
            self.logger.error(f"儲存檔案失敗: {e}")
            raise
    
    def generate_safe_filename(self, file_info: Dict[str, Any], preferred_format: str = None) -> str:
        """生成安全的檔案名稱
        
        Args:
            file_info: 檔案資訊
            preferred_format: 偏好的匯出格式
            
        Returns:
            安全的檔案名稱
        """
        name = file_info.get('name', 'unnamed_file')
        mime_type = file_info.get('mimeType', '')
        
        # 清理檔案名稱
        safe_name = slugify(name, allow_unicode=True)
        
        # 處理副檔名
        if is_google_workspace_file(mime_type):
            # Google Workspace 檔案需要添加匯出格式副檔名
            export_format = self.converter.get_export_format(mime_type, preferred_format)
            extension = self.converter.get_export_extension(mime_type, export_format)
        else:
            # 一般檔案保持原副檔名或從 MIME 類型推斷
            if '.' in safe_name:
                extension = ''  # 已有副檔名
            else:
                extension = get_file_extension_from_mime_type(mime_type)
        
        return safe_name + extension
    
    def get_file_tree(self, folder_id: str, max_depth: int = 5) -> Dict[str, Any]:
        """取得資料夾樹狀結構
        
        Args:
            folder_id: 根資料夾 ID
            max_depth: 最大深度
            
        Returns:
            樹狀結構字典
        """
        if not validate_file_id(folder_id):
            raise ValidationError('folder_id', folder_id, "無效的資料夾 ID 格式")
        
        def build_tree(current_folder_id: str, current_depth: int) -> Dict[str, Any]:
            if current_depth > max_depth:
                return {'error': 'Max depth reached'}
            
            try:
                folder_info = self.get_file_info(current_folder_id)
                files = self.get_folder_contents(current_folder_id, recursive=False)
                
                tree = {
                    'id': current_folder_id,
                    'name': folder_info.get('name'),
                    'type': 'folder',
                    'children': []
                }
                
                for file_info in files:
                    if file_info.get('mimeType') == 'application/vnd.google-apps.folder':
                        # 遞迴處理子資料夾
                        subtree = build_tree(file_info['id'], current_depth + 1)
                        tree['children'].append(subtree)
                    else:
                        # 添加檔案
                        tree['children'].append({
                            'id': file_info['id'],
                            'name': file_info.get('name'),
                            'type': 'file',
                            'mimeType': file_info.get('mimeType'),
                            'size': file_info.get('size')
                        })
                
                return tree
                
            except Exception as e:
                self.logger.warning(f"建立樹狀結構失敗: {e}")
                return {'error': str(e)}
        
        return build_tree(folder_id, 0)
    
    def search_files(self, query: str, folder_id: str = None, file_type: str = None) -> List[Dict[str, Any]]:
        """搜尋檔案
        
        Args:
            query: 搜尋關鍵字
            folder_id: 限制搜尋範圍的資料夾 ID
            file_type: 檔案類型篩選
            
        Returns:
            搜尋結果清單
        """
        try:
            drive_service = self._get_drive_service()
            
            # 建立搜尋查詢
            search_query = f"name contains '{query}' and trashed=false"
            
            if folder_id:
                search_query += f" and '{folder_id}' in parents"
            
            if file_type:
                if file_type == 'folder':
                    search_query += " and mimeType='application/vnd.google-apps.folder'"
                elif file_type == 'document':
                    search_query += " and mimeType contains 'document'"
                elif file_type == 'image':
                    search_query += " and mimeType contains 'image'"
                # 可以添加更多檔案類型
            
            results = drive_service.files().list(
                q=search_query,
                pageSize=100,
                fields='files(id,name,mimeType,size,createdTime,modifiedTime,parents,webViewLink)'
            ).execute()
            
            files = results.get('files', [])
            self.logger.info(f"搜尋結果: {len(files)} 個檔案")
            
            return files
            
        except Exception as e:
            self.logger.error(f"搜尋檔案失敗: {e}")
            raise
    
    def get_download_stats(self, file_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """計算下載統計資訊
        
        Args:
            file_list: 檔案清單
            
        Returns:
            統計資訊
        """
        total_files = len(file_list)
        total_size = 0
        file_types = {}
        google_workspace_files = 0
        
        for file_info in file_list:
            # 計算大小
            size = file_info.get('size')
            if size and size.isdigit():
                total_size += int(size)
            
            # 統計檔案類型
            mime_type = file_info.get('mimeType', 'unknown')
            file_types[mime_type] = file_types.get(mime_type, 0) + 1
            
            # 統計 Google Workspace 檔案
            if is_google_workspace_file(mime_type):
                google_workspace_files += 1
        
        return {
            'total_files': total_files,
            'total_size': total_size,
            'file_types': file_types,
            'google_workspace_files': google_workspace_files,
            'regular_files': total_files - google_workspace_files
        }

    def get_folder_contents_lite(self, folder_id: str) -> List[Dict[str, Any]]:
        """輕量級取得資料夾內容（僅用於 UI 瀏覽）
        
        Args:
            folder_id: 資料夾 ID
            
        Returns:
            檔案清單（不遞迴，限制數量）
        """
        if not validate_file_id(folder_id):
            raise ValidationError('folder_id', folder_id, "無效的資料夾 ID 格式")
        
        try:
            drive_service = self._get_drive_service()
            
            # 檢查是否為資料夾
            folder_info = self.get_file_info(folder_id)
            if folder_info.get('mimeType') != 'application/vnd.google-apps.folder':
                raise ValidationError('folder_id', folder_id, "指定的 ID 不是資料夾")
            
            # 輕量級查詢：只取前 100 個項目，不分頁
            query = f"'{folder_id}' in parents and trashed=false"
            
            def api_call():
                return drive_service.files().list(
                    q=query,
                    pageSize=100,  # 限制為 100 個項目
                    orderBy='folder,name',  # 資料夾優先，然後按名稱排序
                    fields='files(id,name,mimeType,size,modifiedTime)'  # 只取必要欄位
                ).execute()
            
            results = self._safe_api_call(api_call)
            files = results.get('files', [])
            
            self.logger.debug(f"輕量級載入資料夾內容: {len(files)} 個項目")
            return files
            
        except Exception as e:
            self.logger.error(f"輕量級載入失敗: {e} (資料夾ID: {folder_id})")
            # 發生錯誤時返回空列表，而不是拋出異常
            return []


# 全域檔案處理器實例
file_handler = FileHandler() 