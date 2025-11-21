"""
資料夾瀏覽頁面模組
提供 Google Drive 資料夾瀏覽和選擇功能
"""

import streamlit as st
import time
import plotly.express as px
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.core.file_handler import file_handler
from src.core.downloader import download_manager
from src.utils.helpers import format_bytes
from src.utils.logger import get_logger

from ..utils.session_manager import SessionManager
from ..utils.ui_helpers import format_file_size, get_file_icon, get_file_color, truncate_filename
from ..components.file_cards import (
    render_folder_grid,
    render_file_grid,
    render_file_table,
    render_file_type_stats
)

logger = get_logger(__name__)


def render_browser_page():
    """渲染資料夾瀏覽頁面"""
    st.header("📁 Google Drive 資料夾瀏覽")

    # 初始化導航狀態
    _init_navigation_state()

    # 路徑導航
    _render_breadcrumb()

    st.markdown("---")

    # 搜尋和篩選
    search_query, file_type_filter, sort_order = _render_search_filter()

    # 載入資料夾內容
    folder_contents = _load_folder_contents()

    if not folder_contents:
        st.info("📭 此資料夾是空的或載入失敗")
        return

    # 應用篩選和排序
    folder_contents = _apply_filters(folder_contents, search_query, file_type_filter, sort_order)

    # 分離資料夾和檔案
    folders = [item for item in folder_contents if item.get('mimeType') == 'application/vnd.google-apps.folder']
    files = [item for item in folder_contents if item.get('mimeType') != 'application/vnd.google-apps.folder']

    # 統計資訊
    _render_folder_stats(folders, files)

    st.markdown("---")

    # 快速操作區域
    if SessionManager.get('current_folder_id') is not None:
        _render_quick_actions()

    # 顯示資料夾和檔案
    _render_folder_contents(folders, files)

    # 下載選項對話框
    if SessionManager.get('show_download_options', False):
        _render_download_options()

    # 資料夾預覽對話框
    if SessionManager.get('show_folder_preview', False):
        _render_folder_preview()


def _init_navigation_state():
    """初始化導航狀態"""
    if SessionManager.get('current_folder_id') is None:
        SessionManager.set('current_folder_name', "我的雲端硬碟")
        if not SessionManager.get('folder_path'):
            SessionManager.set('folder_path', ["我的雲端硬碟"])
            SessionManager.set('folder_id_path', [None])


def _render_breadcrumb():
    """渲染麵包屑導航"""
    st.markdown("### 📍 當前位置")

    folder_path = SessionManager.get('folder_path', ["我的雲端硬碟"])
    folder_id_path = SessionManager.get('folder_id_path', [None])

    breadcrumb_cols = st.columns(len(folder_path))
    for i, (folder_name, folder_id) in enumerate(zip(folder_path, folder_id_path)):
        with breadcrumb_cols[i]:
            if st.button(f"📁 {folder_name}", key=f"breadcrumb_{i}"):
                SessionManager.navigate_to_breadcrumb(i)
                st.rerun()


def _render_search_filter():
    """渲染搜尋和篩選區域"""
    with st.expander("🔍 搜尋與篩選", expanded=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            search_query = st.text_input("🔍 搜尋檔案/資料夾", placeholder="輸入關鍵字...")

        with col2:
            file_type_filter = st.selectbox(
                "📄 檔案類型篩選",
                ["全部", "僅資料夾", "僅檔案", "Google 文件", "圖片", "影片", "PDF"],
                index=0
            )

        with col3:
            sort_order = st.selectbox(
                "📊 排序方式",
                ["名稱 (A-Z)", "名稱 (Z-A)", "修改時間 (新→舊)", "修改時間 (舊→新)", "大小 (大→小)", "大小 (小→大)"],
                index=0
            )

    return search_query, file_type_filter, sort_order


def _load_folder_contents():
    """載入資料夾內容"""
    current_folder_id = SessionManager.get('current_folder_id')

    with st.spinner("🔄 載入資料夾內容..."):
        max_retries = 3

        for attempt in range(max_retries):
            try:
                if current_folder_id is None:
                    return file_handler.get_folder_contents_lite('root')
                else:
                    return file_handler.get_folder_contents_lite(current_folder_id)
            except Exception as e:
                logger.error(f"載入資料夾失敗 (嘗試 {attempt + 1}/{max_retries}): {e}")

                if attempt < max_retries - 1:
                    st.warning(f"⚠️ 載入資料夾時遇到問題，正在重試... ({attempt + 1}/{max_retries})")
                    time.sleep(1.0 * (attempt + 1))
                else:
                    st.error(f"❌ 載入資料夾失敗: {e}")
                    st.info("💡 請檢查網路連接，然後點擊「重新整理」按鈕重試")
                    return []

    return []


def _apply_filters(folder_contents, search_query, file_type_filter, sort_order):
    """應用篩選和排序"""
    # 搜尋篩選
    if search_query:
        folder_contents = [
            item for item in folder_contents
            if search_query.lower() in item.get('name', '').lower()
        ]

    # 檔案類型篩選
    type_filters = {
        "僅資料夾": lambda x: x.get('mimeType') == 'application/vnd.google-apps.folder',
        "僅檔案": lambda x: x.get('mimeType') != 'application/vnd.google-apps.folder',
        "Google 文件": lambda x: 'google-apps' in x.get('mimeType', ''),
        "圖片": lambda x: x.get('mimeType', '').startswith('image/'),
        "影片": lambda x: x.get('mimeType', '').startswith('video/'),
        "PDF": lambda x: x.get('mimeType') == 'application/pdf',
    }

    if file_type_filter in type_filters:
        folder_contents = [item for item in folder_contents if type_filters[file_type_filter](item)]

    # 排序
    sort_keys = {
        "名稱 (A-Z)": (lambda x: x.get('name', '').lower(), False),
        "名稱 (Z-A)": (lambda x: x.get('name', '').lower(), True),
        "修改時間 (新→舊)": (lambda x: x.get('modifiedTime', ''), True),
        "修改時間 (舊→新)": (lambda x: x.get('modifiedTime', ''), False),
        "大小 (大→小)": (lambda x: int(x.get('size', 0) or 0), True),
        "大小 (小→大)": (lambda x: int(x.get('size', 0) or 0), False),
    }

    if sort_order in sort_keys:
        key_func, reverse = sort_keys[sort_order]
        folder_contents.sort(key=key_func, reverse=reverse)

    return folder_contents


def _render_folder_stats(folders, files):
    """渲染資料夾統計"""
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("📁 資料夾數量", len(folders))

    with col2:
        st.metric("📄 檔案數量", len(files))

    with col3:
        if files:
            total_size = sum(int(f.get('size', 0) or 0) for f in files)
            st.metric("💾 總大小", format_bytes(total_size))
        else:
            st.metric("💾 總大小", "N/A")


def _render_quick_actions():
    """渲染快速操作區域"""
    with st.container():
        st.markdown("### ⚡ 快速操作")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📥 下載整個資料夾", use_container_width=True, type="primary"):
                current_folder = {
                    'id': SessionManager.get('current_folder_id'),
                    'name': SessionManager.get('current_folder_name')
                }
                SessionManager.set('selected_folder_for_download', current_folder)
                SessionManager.set('show_download_options', True)
                st.rerun()

        with col2:
            if st.button("🔄 重新整理", use_container_width=True):
                st.rerun()

        with col3:
            if st.button("🔙 回到上層", use_container_width=True):
                if SessionManager.navigate_up():
                    st.rerun()

    st.markdown("---")


def _render_folder_contents(folders, files):
    """渲染資料夾和檔案內容"""
    # 資料夾顯示
    if folders:
        st.subheader("📁 資料夾")
        render_folder_grid(
            folders,
            on_enter=_on_folder_enter,
            on_download=_on_folder_download,
            columns=3
        )
        st.markdown("---")

    # 檔案顯示
    if files:
        st.subheader("📄 檔案")
        view_mode = st.radio("顯示模式", ["表格視圖", "卡片視圖"], horizontal=True)

        if view_mode == "表格視圖":
            render_file_table(files, max_items=50)
        else:
            render_file_grid(files, columns=4, max_items=20)


def _on_folder_enter(folder_id: str, folder_name: str):
    """資料夾進入回調"""
    SessionManager.navigate_to_folder(folder_id, folder_name)
    st.rerun()


def _on_folder_download(folder: dict):
    """資料夾下載回調"""
    SessionManager.set('selected_folder_for_download', folder)
    SessionManager.set('show_download_options', True)
    st.rerun()


def _render_download_options():
    """渲染下載選項對話框"""
    st.markdown("---")
    st.subheader("📥 下載設定")

    selected_folder = SessionManager.get('selected_folder_for_download')
    if not selected_folder:
        return

    st.info(f"準備下載資料夾: **{selected_folder['name']}**")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**下載選項**")
        include_subfolders = st.checkbox("包含子資料夾", value=True)
        max_concurrent = st.slider("最大並發數", min_value=1, max_value=10, value=3)

        st.markdown("**Google Workspace 檔案轉換**")
        office_conversion = st.checkbox(
            "🔄 自動轉換為 Office 格式",
            value=True,
            help="Google文件→Word、試算表→Excel、簡報→PowerPoint"
        )

        if office_conversion:
            st.info("✅ 將自動轉換：Google文件→Word (.docx)、試算表→Excel (.xlsx)、簡報→PowerPoint (.pptx)")
            preferred_format = None
        else:
            preferred_format = st.selectbox(
                "手動選擇格式",
                ["pdf", "docx", "xlsx", "pptx", "txt", "html"],
                index=0
            )

    with col2:
        st.markdown("**輸出設定**")
        output_path = st.text_input(
            "輸出路徑",
            value=str(Path("output") / selected_folder['name']),
            help="下載檔案的儲存位置"
        )

        # 預估資訊
        try:
            with st.spinner("計算資料夾大小..."):
                folder_stats = file_handler.get_download_stats(
                    file_handler.get_folder_contents(selected_folder['id'], recursive=include_subfolders, max_depth=5)
                )

            st.markdown("**預估資訊**")
            st.text(f"檔案數量: {folder_stats.get('total_files', 0)}")
            st.text(f"總大小: {format_bytes(folder_stats.get('total_size', 0))}")

        except Exception as e:
            st.warning(f"無法計算資料夾大小: {e}")

    # 按鈕區域
    btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 1])

    with btn_col1:
        if st.button("✅ 開始下載", type="primary", use_container_width=True):
            _start_download(selected_folder, output_path, max_concurrent, preferred_format)

    with btn_col2:
        if st.button("❌ 取消", use_container_width=True):
            SessionManager.clear_download_state()
            st.rerun()

    with btn_col3:
        if st.button("🔍 預覽內容", use_container_width=True):
            SessionManager.set('show_folder_preview', True)
            st.rerun()


def _start_download(selected_folder, output_path, max_concurrent, preferred_format):
    """開始下載"""
    try:
        folder_url = f"https://drive.google.com/drive/folders/{selected_folder['id']}"

        task_id = download_manager.create_task(
            source_url=folder_url,
            output_path=Path(output_path),
            max_concurrent=max_concurrent,
            preferred_format=preferred_format
        )

        st.success(f"✅ 下載任務已創建！任務 ID: {task_id}")
        st.info("📋 任務將在後台進行分析和下載，請到「任務管理」頁面查看進度")

        SessionManager.clear_download_state()
        st.balloons()
        time.sleep(2)
        st.rerun()

    except Exception as e:
        st.error(f"❌ 創建下載任務失敗: {e}")


def _render_folder_preview():
    """渲染資料夾預覽對話框"""
    st.markdown("---")
    st.subheader("🔍 資料夾詳細預覽")

    selected_folder = SessionManager.get('selected_folder_for_download')
    if not selected_folder:
        return

    st.info(f"預覽資料夾: **{selected_folder['name']}**")

    try:
        with st.spinner("載入資料夾內容詳細資訊..."):
            preview_contents = file_handler.get_folder_contents(selected_folder['id'], recursive=True, max_depth=3)

        # 統計分析
        total_files = len([f for f in preview_contents if f.get('mimeType') != 'application/vnd.google-apps.folder'])
        total_folders = len([f for f in preview_contents if f.get('mimeType') == 'application/vnd.google-apps.folder'])
        total_size = sum(int(f.get('size', 0) or 0) for f in preview_contents)

        # 檔案類型統計
        file_types = render_file_type_stats(preview_contents)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 📊 內容統計")
            st.metric("📁 子資料夾", total_folders)
            st.metric("📄 檔案總數", total_files)
            st.metric("💾 總大小", format_bytes(total_size))

            # 檔案類型分佈圓餅圖
            if file_types:
                fig_pie = px.pie(
                    values=list(file_types.values()),
                    names=list(file_types.keys()),
                    title="檔案類型分佈"
                )
                st.plotly_chart(fig_pie, use_container_width=True)

        with col2:
            st.markdown("### 📝 檔案類型詳細")
            for file_type, count in file_types.items():
                st.text(f"{file_type}: {count} 個")

            # 最大的檔案
            largest_files = sorted(
                [f for f in preview_contents if f.get('size')],
                key=lambda x: int(x.get('size', 0)),
                reverse=True
            )[:5]

            if largest_files:
                st.markdown("### 📈 最大的檔案")
                for file in largest_files:
                    name = truncate_filename(file['name'], 30)
                    size = format_bytes(int(file.get('size', 0)))
                    st.text(f"📄 {name} - {size}")

        # 操作按鈕
        btn_col1, btn_col2 = st.columns(2)

        with btn_col1:
            if st.button("📥 確認下載此資料夾", type="primary", use_container_width=True):
                SessionManager.set('show_folder_preview', False)
                st.rerun()

        with btn_col2:
            if st.button("❌ 關閉預覽", use_container_width=True):
                SessionManager.set('show_folder_preview', False)
                st.rerun()

    except Exception as e:
        st.error(f"載入資料夾預覽失敗: {e}")
        if st.button("❌ 關閉預覽"):
            SessionManager.set('show_folder_preview', False)
            st.rerun()
