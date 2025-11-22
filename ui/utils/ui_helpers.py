"""
UI 輔助函數模組
提供常用的 UI 輔助功能
"""

import html
from typing import Tuple


def format_file_size(size_bytes: int) -> str:
    """格式化檔案大小"""
    if size_bytes is None or size_bytes == 0:
        return "N/A"

    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def get_file_icon(mime_type: str) -> str:
    """根據 MIME 類型取得檔案圖示"""
    if not mime_type:
        return "📄"

    icon_map = {
        'application/vnd.google-apps.folder': '📁',
        'application/vnd.google-apps.document': '📝',
        'application/vnd.google-apps.spreadsheet': '📊',
        'application/vnd.google-apps.presentation': '📽️',
        'application/vnd.google-apps.drawing': '🎨',
        'application/vnd.google-apps.form': '📋',
        'application/pdf': '📕',
    }

    # 直接匹配
    if mime_type in icon_map:
        return icon_map[mime_type]

    # 前綴匹配
    if mime_type.startswith('image/'):
        return '🖼️'
    if mime_type.startswith('video/'):
        return '🎥'
    if mime_type.startswith('audio/'):
        return '🎵'
    if 'zip' in mime_type or 'compressed' in mime_type:
        return '📦'
    if 'text/' in mime_type:
        return '📄'

    return '📄'


def get_file_color(mime_type: str) -> str:
    """根據 MIME 類型取得顏色"""
    if not mime_type:
        return "#757575"

    color_map = {
        'application/vnd.google-apps.document': '#4285f4',  # Google 藍
        'application/vnd.google-apps.spreadsheet': '#34a853',  # Google 綠
        'application/vnd.google-apps.presentation': '#fbbc04',  # Google 黃
        'application/vnd.google-apps.drawing': '#ea4335',  # Google 紅
        'application/pdf': '#ff5722',  # 橙色
    }

    if mime_type in color_map:
        return color_map[mime_type]

    if mime_type.startswith('image/'):
        return '#ea4335'
    if mime_type.startswith('video/'):
        return '#9c27b0'
    if mime_type.startswith('audio/'):
        return '#00bcd4'

    return '#757575'


def truncate_filename(filename: str, max_length: int = 20) -> str:
    """截斷檔案名稱"""
    if len(filename) <= max_length:
        return filename
    return filename[:max_length - 3] + '...'


def escape_html(text: str) -> str:
    """轉義 HTML 特殊字符"""
    return html.escape(text)


def create_file_card_html(
    icon: str,
    name: str,
    subtitle: str,
    color: str = "#757575",
    min_height: str = "120px"
) -> str:
    """創建檔案卡片 HTML"""
    safe_name = escape_html(name)
    safe_subtitle = escape_html(subtitle)

    return f"""
    <div style="
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 15px;
        margin: 5px;
        background-color: #f8f9fa;
        text-align: center;
        min-height: {min_height};
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        transition: transform 0.2s;
        border-left: 4px solid {color};
    ">
        <div>
            <div style="font-size: 24px; margin-bottom: 8px;">{icon}</div>
            <div style="font-weight: bold; font-size: 14px; margin-bottom: 5px; word-wrap: break-word; text-align: center; color: #333;">
                {safe_name}
            </div>
            <div style="font-size: 12px; color: #666;">
                {safe_subtitle}
            </div>
        </div>
    </div>
    """


def create_folder_card_html(name: str, modified_time: str) -> str:
    """創建資料夾卡片 HTML"""
    return create_file_card_html(
        icon="📁",
        name=truncate_filename(name, 20),
        subtitle=f"修改時間: {modified_time}",
        color="#4285f4",
        min_height="120px"
    )


def create_compact_file_card_html(
    icon: str,
    name: str,
    size: str,
    color: str = "#757575"
) -> str:
    """創建緊湊型檔案卡片 HTML"""
    safe_name = escape_html(truncate_filename(name, 15))

    return f"""
    <div style="
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 10px;
        margin: 3px;
        background-color: #fff;
        text-align: center;
        min-height: 100px;
        border-left: 4px solid {color};
    ">
        <div style="font-size: 20px; margin-bottom: 5px;">{icon}</div>
        <div style="font-size: 12px; font-weight: bold; margin-bottom: 3px; word-wrap: break-word;">
            {safe_name}
        </div>
        <div style="font-size: 10px; color: #666;">
            {size}
        </div>
    </div>
    """


def get_status_icon(status: str) -> str:
    """取得狀態圖示"""
    status_icons = {
        'pending': '⏳',
        'preparing': '🔄',
        'downloading': '📥',
        'completed': '✅',
        'failed': '❌',
        'cancelled': '🛑',
        'paused': '⏸️'
    }
    return status_icons.get(status.lower(), '❓')


def format_duration(seconds: float) -> str:
    """格式化時間長度"""
    if seconds < 60:
        return f"{int(seconds)}秒"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}分{secs}秒"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}小時{minutes}分"
