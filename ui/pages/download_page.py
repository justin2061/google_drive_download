"""
下載頁面模組
處理檔案下載任務的建立和管理
"""

import streamlit as st
import asyncio
import time
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.core.downloader import download_manager
from src.core.file_handler import file_handler
from src.utils.config import get_config
from src.utils.helpers import extract_file_id_from_url, format_bytes


def render_download_page():
    """渲染下載頁面"""
    st.title("📥 檔案下載")

    # 新建下載任務
    with st.container():
        st.subheader("🆕 新建下載任務")
        _render_download_form()


def _render_download_form():
    """渲染下載表單"""
    col1, col2 = st.columns([3, 1])

    with col1:
        url = st.text_input(
            "Google Drive 連結或檔案 ID",
            placeholder="https://drive.google.com/... 或直接輸入檔案 ID",
            help="支援 Google Drive 分享連結或直接輸入檔案/資料夾 ID"
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        preview = st.button("👁️ 預覽", help="預覽檔案資訊")

    # 進階設定
    task_name, output_dir, max_concurrent, preferred_format, auto_start = _render_advanced_settings()

    # 預覽檔案資訊
    if preview and url:
        _preview_file(url)

    # 建立任務按鈕
    _render_create_task_button(url, output_dir, task_name, max_concurrent, preferred_format, auto_start)


def _render_advanced_settings():
    """渲染進階設定"""
    with st.expander("⚙️ 進階設定"):
        col1, col2, col3 = st.columns(3)

        with col1:
            task_name = st.text_input("任務名稱", placeholder="可選，留空自動生成")
            output_dir = st.text_input(
                "輸出目錄",
                value=get_config('download.default_output_dir', './downloads')
            )

        with col2:
            max_concurrent = st.slider(
                "並發下載數",
                min_value=1,
                max_value=10,
                value=get_config('download.max_concurrent', 5)
            )

            format_options = ["自動選擇 Office 格式", "docx", "pdf", "xlsx", "csv", "pptx", "png", "jpg"]
            preferred_format = st.selectbox(
                "偏好格式",
                format_options,
                help="自動選擇將Google文件轉為Word、試算表轉為Excel、簡報轉為PowerPoint"
            )
            if preferred_format == "自動選擇 Office 格式":
                preferred_format = None

        with col3:
            auto_start = st.checkbox("建立後自動開始", value=True)

    return task_name, output_dir, max_concurrent, preferred_format, auto_start


def _preview_file(url: str):
    """預覽檔案資訊"""
    try:
        file_id = extract_file_id_from_url(url)
        if file_id:
            with st.spinner("正在取得檔案資訊..."):
                file_info = file_handler.get_file_info(file_id)

            st.success("✅ 檔案資訊取得成功")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"**📝 名稱:** {file_info.get('name')}")
                st.markdown(f"**📋 類型:** {file_info.get('mimeType')}")
                if file_info.get('size'):
                    st.markdown(f"**💾 大小:** {format_bytes(int(file_info['size']))}")

            with col2:
                st.markdown(f"**🆔 ID:** {file_info.get('id')}")
                st.markdown(f"**📅 修改時間:** {file_info.get('modifiedTime')}")

            # 如果是資料夾，顯示內容統計
            if file_info.get('mimeType') == 'application/vnd.google-apps.folder':
                with st.spinner("正在分析資料夾內容..."):
                    contents = file_handler.get_folder_contents(file_id, recursive=True, max_depth=3)
                    stats = file_handler.get_download_stats(contents)

                st.info(f"📂 資料夾包含 {stats['total_files']} 個檔案，總大小 {format_bytes(stats['total_size'])}")
        else:
            st.error("❌ 無法解析檔案 ID")

    except Exception as e:
        st.error(f"❌ 取得檔案資訊失敗: {e}")


def _render_create_task_button(url, output_dir, task_name, max_concurrent, preferred_format, auto_start):
    """渲染建立任務按鈕"""
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if st.button("🚀 建立下載任務", type="primary", use_container_width=True):
            if not url:
                st.error("請輸入 Google Drive 連結或檔案 ID")
            else:
                try:
                    task_id = download_manager.create_task(
                        source_url=url,
                        output_path=output_dir,
                        name=task_name or None,
                        max_concurrent=max_concurrent,
                        preferred_format=preferred_format
                    )

                    st.success(f"✅ 任務建立成功！ID: {task_id[:8]}...")

                    if auto_start:
                        asyncio.run(download_manager.start_task(task_id))
                        st.info("🚀 任務已自動開始")

                    time.sleep(1)
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ 建立任務失敗: {e}")
