"""
通用輔助函數
提供常用的工具函數
"""

import re
import unicodedata
from typing import Optional, Union
from pathlib import Path


def slugify(value: str, allow_unicode: bool = False) -> str:
    """
    將字串轉換為安全的檔案名稱
    
    Args:
        value: 原始字串
        allow_unicode: 是否允許 Unicode 字符
        
    Returns:
        安全的檔案名稱
    """
    value = str(value)
    
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    
    # 移除或替換不安全的字符
    value = re.sub(r'[^\w\s\-_.]', '', value.strip())
    
    # 替換多個空白為單一底線
    value = re.sub(r'[\s]+', '_', value)
    
    # 移除連續的特殊字符
    value = re.sub(r'[_\-\.]+', lambda m: m.group(0)[0], value)
    
    # 限制長度（Windows 檔案名最大 255 字符）
    if len(value) > 200:
        name, ext = Path(value).stem, Path(value).suffix
        value = name[:200-len(ext)] + ext
    
    return value


def format_size(size_bytes: Union[int, float]) -> str:
    """
    格式化檔案大小
    
    Args:
        size_bytes: 檔案大小（位元組）
        
    Returns:
        格式化的檔案大小字串
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB", "PB"]
    i = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    if i == 0:
        return f"{int(size)} {size_names[i]}"
    else:
        return f"{size:.1f} {size_names[i]}"


def format_time(seconds: Optional[float]) -> str:
    """
    格式化時間
    
    Args:
        seconds: 秒數
        
    Returns:
        格式化的時間字串
    """
    if seconds is None or seconds < 0:
        return "N/A"
    
    if seconds < 60:
        return f"{int(seconds)}秒"
    
    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    
    if minutes < 60:
        return f"{minutes}分{remaining_seconds}秒"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    if hours < 24:
        return f"{hours}小時{remaining_minutes}分"
    
    days = hours // 24
    remaining_hours = hours % 24
    
    return f"{days}天{remaining_hours}小時"


def format_speed(bytes_per_second: float) -> str:
    """
    格式化下載速度
    
    Args:
        bytes_per_second: 每秒位元組數
        
    Returns:
        格式化的速度字串
    """
    return f"{format_size(bytes_per_second)}/s"


def sanitize_path(path: str) -> str:
    """
    清理檔案路徑，確保安全性
    
    Args:
        path: 原始路徑
        
    Returns:
        清理後的路徑
    """
    # 移除危險的路徑元素
    path = path.replace('..', '').replace('//', '/')
    
    # 分割路徑並清理每個部分
    parts = Path(path).parts
    clean_parts = []
    
    for part in parts:
        if part and part not in ('.', '..'):
            clean_parts.append(slugify(part, allow_unicode=True))
    
    return str(Path(*clean_parts)) if clean_parts else ''


def extract_file_id_from_url(url: str) -> Optional[str]:
    """
    從 Google Drive URL 中提取檔案 ID
    
    Args:
        url: Google Drive URL
        
    Returns:
        檔案 ID 或 None
    """
    patterns = [
        r'/file/d/([a-zA-Z0-9-_]+)',
        r'id=([a-zA-Z0-9-_]+)',
        r'/folders/([a-zA-Z0-9-_]+)',
        r'^([a-zA-Z0-9-_]+)$'  # 直接是 ID
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


def validate_file_id(file_id: str) -> bool:
    """
    驗證 Google Drive 檔案 ID 格式
    
    Args:
        file_id: 檔案 ID
        
    Returns:
        True if valid, False otherwise
    """
    if not file_id or not isinstance(file_id, str):
        return False
    
    # Google Drive 檔案 ID 通常是 28-44 個字符的 Base64 編碼
    pattern = r'^[a-zA-Z0-9_-]{28,44}$'
    return bool(re.match(pattern, file_id))


def get_file_extension_from_mime_type(mime_type: str) -> str:
    """
    從 MIME 類型取得檔案副檔名
    
    Args:
        mime_type: MIME 類型
        
    Returns:
        檔案副檔名（包含點號）
    """
    mime_to_ext = {
        # Google Workspace 檔案
        'application/vnd.google-apps.document': '.docx',
        'application/vnd.google-apps.spreadsheet': '.xlsx',
        'application/vnd.google-apps.presentation': '.pptx',
        'application/vnd.google-apps.drawing': '.png',
        'application/vnd.google-apps.form': '.pdf',
        
        # 常見檔案類型
        'application/pdf': '.pdf',
        'application/msword': '.doc',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
        'application/vnd.ms-excel': '.xls',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
        'application/vnd.ms-powerpoint': '.ppt',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
        
        # 圖片檔案
        'image/jpeg': '.jpg',
        'image/png': '.png',
        'image/gif': '.gif',
        'image/bmp': '.bmp',
        'image/svg+xml': '.svg',
        
        # 音訊檔案
        'audio/mpeg': '.mp3',
        'audio/wav': '.wav',
        'audio/ogg': '.ogg',
        
        # 視訊檔案
        'video/mp4': '.mp4',
        'video/avi': '.avi',
        'video/quicktime': '.mov',
        
        # 文字檔案
        'text/plain': '.txt',
        'text/csv': '.csv',
        'text/html': '.html',
        'application/json': '.json',
        'application/xml': '.xml',
        
        # 壓縮檔案
        'application/zip': '.zip',
        'application/x-rar-compressed': '.rar',
        'application/x-7z-compressed': '.7z',
    }
    
    return mime_to_ext.get(mime_type, '')


def create_directory_structure(base_path: str, folder_name: str) -> Path:
    """
    建立目錄結構
    
    Args:
        base_path: 基礎路徑
        folder_name: 資料夾名稱
        
    Returns:
        建立的目錄路徑
    """
    # 清理資料夾名稱
    clean_folder_name = slugify(folder_name, allow_unicode=True)
    
    # 建立完整路徑
    full_path = Path(base_path) / clean_folder_name
    
    # 建立目錄
    full_path.mkdir(parents=True, exist_ok=True)
    
    return full_path


def is_google_workspace_file(mime_type: str) -> bool:
    """
    判斷是否為 Google Workspace 檔案
    
    Args:
        mime_type: MIME 類型
        
    Returns:
        True if Google Workspace file, False otherwise
    """
    return mime_type.startswith('application/vnd.google-apps.')


def calculate_percentage(current: float, total: float) -> float:
    """
    計算百分比
    
    Args:
        current: 當前值
        total: 總值
        
    Returns:
        百分比（0-100）
    """
    if total == 0:
        return 0.0
    return min(100.0, max(0.0, (current / total) * 100))


def truncate_string(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    截斷字串
    
    Args:
        text: 原始字串
        max_length: 最大長度
        suffix: 後綴
        
    Returns:
        截斷後的字串
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


# 為了向後相容性，提供別名
format_bytes = format_size
format_duration = format_time 