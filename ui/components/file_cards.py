"""
檔案卡片組件
提供檔案和資料夾的顯示組件
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Callable, Optional

from ..utils.ui_helpers import (
    get_file_icon,
    get_file_color,
    truncate_filename,
    create_folder_card_html,
    create_compact_file_card_html,
    format_file_size
)


def render_folder_card(
    folder: Dict[str, Any],
    on_enter: Callable[[str, str], None],
    on_download: Callable[[Dict], None],
    key_prefix: str = ""
):
    """渲染單個資料夾卡片

    Args:
        folder: 資料夾資訊
        on_enter: 進入資料夾回調函數
        on_download: 下載回調函數
        key_prefix: 按鈕 key 前綴
    """
    folder_name = folder.get('name', '未命名資料夾')
    modified_time = folder.get('modifiedTime', 'N/A')[:10] if folder.get('modifiedTime') else 'N/A'

    # 渲染卡片 HTML
    st.markdown(
        create_folder_card_html(folder_name, modified_time),
        unsafe_allow_html=True
    )

    # 操作按鈕
    btn_col1, btn_col2 = st.columns(2)

    with btn_col1:
        if st.button("🔍 進入", key=f"{key_prefix}enter_{folder['id']}", use_container_width=True):
            on_enter(folder['id'], folder['name'])

    with btn_col2:
        if st.button("📥 下載", key=f"{key_prefix}download_{folder['id']}", use_container_width=True):
            on_download(folder)


def render_folder_grid(
    folders: List[Dict[str, Any]],
    on_enter: Callable[[str, str], None],
    on_download: Callable[[Dict], None],
    columns: int = 3
):
    """渲染資料夾網格

    Args:
        folders: 資料夾列表
        on_enter: 進入資料夾回調函數
        on_download: 下載回調函數
        columns: 每行列數
    """
    if not folders:
        return

    rows = (len(folders) + columns - 1) // columns

    for row in range(rows):
        cols = st.columns(columns)
        for col_idx in range(columns):
            folder_idx = row * columns + col_idx
            if folder_idx < len(folders):
                folder = folders[folder_idx]
                with cols[col_idx]:
                    with st.container():
                        render_folder_card(
                            folder,
                            on_enter,
                            on_download,
                            key_prefix=f"grid_row{row}_"
                        )


def render_file_card(file: Dict[str, Any], key_prefix: str = ""):
    """渲染單個檔案卡片"""
    mime_type = file.get('mimeType', '')
    icon = get_file_icon(mime_type)
    color = get_file_color(mime_type)
    name = file.get('name', '未命名檔案')
    size = format_file_size(int(file.get('size', 0))) if file.get('size') else 'N/A'

    st.markdown(
        create_compact_file_card_html(icon, name, size, color),
        unsafe_allow_html=True
    )


def render_file_grid(files: List[Dict[str, Any]], columns: int = 4, max_items: int = 20):
    """渲染檔案網格

    Args:
        files: 檔案列表
        columns: 每行列數
        max_items: 最多顯示數量
    """
    if not files:
        return

    display_files = files[:max_items]
    rows = (len(display_files) + columns - 1) // columns

    for row in range(rows):
        cols = st.columns(columns)
        for col_idx in range(columns):
            file_idx = row * columns + col_idx
            if file_idx < len(display_files):
                file = display_files[file_idx]
                with cols[col_idx]:
                    render_file_card(file, key_prefix=f"file_grid_{row}_{col_idx}_")

    if len(files) > max_items:
        st.info(f"顯示前 {max_items} 個檔案，共 {len(files)} 個檔案")


def render_file_table(files: List[Dict[str, Any]], max_items: int = 50):
    """渲染檔案表格

    Args:
        files: 檔案列表
        max_items: 最多顯示數量
    """
    if not files:
        st.info("📭 沒有檔案")
        return

    file_data = []
    for file in files[:max_items]:
        mime_type = file.get('mimeType', '')
        icon = get_file_icon(mime_type)
        name = file.get('name', '未命名檔案')
        name_display = truncate_filename(name, 40)

        file_data.append({
            '類型': icon,
            '名稱': name_display,
            '大小': format_file_size(int(file.get('size', 0))) if file.get('size') else 'N/A',
            '修改時間': file.get('modifiedTime', 'N/A')[:10] if file.get('modifiedTime') else 'N/A'
        })

    if file_data:
        df = pd.DataFrame(file_data)
        st.dataframe(df, use_container_width=True)

        if len(files) > max_items:
            st.info(f"顯示前 {max_items} 個檔案，共 {len(files)} 個檔案")


def render_file_type_stats(files: List[Dict[str, Any]]):
    """渲染檔案類型統計"""
    if not files:
        return {}

    file_types = {}
    for item in files:
        if item.get('mimeType') != 'application/vnd.google-apps.folder':
            mime_type = item.get('mimeType', 'unknown')
            if 'google-apps.document' in mime_type:
                file_types['Google 文件'] = file_types.get('Google 文件', 0) + 1
            elif 'google-apps.spreadsheet' in mime_type:
                file_types['Google 試算表'] = file_types.get('Google 試算表', 0) + 1
            elif 'google-apps.presentation' in mime_type:
                file_types['Google 簡報'] = file_types.get('Google 簡報', 0) + 1
            elif mime_type.startswith('image/'):
                file_types['圖片'] = file_types.get('圖片', 0) + 1
            elif mime_type.startswith('video/'):
                file_types['影片'] = file_types.get('影片', 0) + 1
            elif 'pdf' in mime_type:
                file_types['PDF'] = file_types.get('PDF', 0) + 1
            else:
                file_types['其他'] = file_types.get('其他', 0) + 1

    return file_types
