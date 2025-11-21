"""
側邊欄組件
提供用戶資訊、設定和統計顯示
"""

import streamlit as st
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.core.downloader import download_manager
from src.utils.helpers import format_bytes
from ..utils.session_manager import SessionManager, get_auth_manager, logout


def render_sidebar():
    """渲染側邊欄"""
    with st.sidebar:
        # Logo 和標題
        st.image("https://img.icons8.com/color/96/000000/google-drive.png", width=64)
        st.title("Google Drive 下載工具")

        # 用戶資訊區塊
        _render_user_info()

        st.markdown("---")

        # 設定區塊
        _render_settings()

        st.markdown("---")

        # 統計資訊區塊
        if SessionManager.get('authenticated'):
            _render_statistics()


def _render_user_info():
    """渲染用戶資訊"""
    if SessionManager.get('authenticated') and SessionManager.get('user_info'):
        user_info = SessionManager.get('user_info')

        st.markdown("---")
        st.markdown("### 👤 使用者資訊")
        st.markdown(f"**Email:** {user_info.get('email', 'Unknown')}")
        st.markdown(f"**名稱:** {user_info.get('display_name', 'Unknown')}")

        # 儲存空間資訊
        storage = user_info.get('storage_quota', {})
        if storage:
            used = int(storage.get('usage', 0))
            limit = int(storage.get('limit', 0)) if storage.get('limit') else None

            st.markdown("### 💾 儲存空間")
            st.markdown(f"**已使用:** {format_bytes(used)}")
            if limit:
                st.markdown(f"**總容量:** {format_bytes(limit)}")
                usage_percent = (used / limit) * 100
                st.progress(usage_percent / 100)

        st.markdown("---")

        # 登出按鈕
        if st.button("🚪 登出", use_container_width=True):
            logout()
            st.rerun()


def _render_settings():
    """渲染設定區塊"""
    st.markdown("### ⚙️ 設定")

    # 自動重新整理
    auto_refresh = st.checkbox(
        "🔄 自動重新整理",
        value=SessionManager.get('auto_refresh', False),
        help="每 5 秒自動更新任務狀態"
    )
    SessionManager.set('auto_refresh', auto_refresh)

    # 手動重新整理
    if st.button("🔄 立即重新整理", use_container_width=True):
        st.rerun()

    # 網路診斷按鈕
    if st.button("🔍 網路診斷", use_container_width=True):
        _run_network_diagnostic()


def _run_network_diagnostic():
    """執行網路診斷"""
    with st.spinner("正在檢查網路連接..."):
        try:
            auth_manager = get_auth_manager()
            drive_service = auth_manager.get_drive_service()
            about = drive_service.about().get(fields='user').execute()
            st.success("✅ Google Drive API 連接正常")
        except Exception as e:
            st.error(f"❌ 網路連接問題: {e}")
            st.info("💡 建議：\n1. 檢查網路連接\n2. 嘗試重新登入\n3. 檢查防火牆設定")


def _render_statistics():
    """渲染統計資訊"""
    stats = download_manager.get_summary_stats()

    st.markdown("### 📊 統計")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("總任務", stats['total_tasks'])
        st.metric("已完成", stats['completed_tasks'])

    with col2:
        st.metric("下載中", stats['downloading_tasks'])
        st.metric("失敗", stats['failed_tasks'])
