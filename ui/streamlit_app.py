"""
Streamlit Web 管理介面
提供直觀的圖形化下載管理介面

重構版本：模組化架構
- pages/: 頁面模組
- components/: 可復用組件
- utils/: 工具函數
"""

import streamlit as st
import sys
from pathlib import Path

# 添加專案根目錄到路徑
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.logger import setup_logging, get_logger

# 導入 UI 模組
from ui.utils.session_manager import (
    init_session_state,
    check_authentication,
    SessionManager
)
from ui.components.sidebar import render_sidebar
from ui.pages.auth_page import render_auth_page
from ui.pages.browser_page import render_browser_page
from ui.pages.download_page import render_download_page
from ui.pages.tasks_page import render_tasks_page


# 設定頁面配置
st.set_page_config(
    page_title="Google Drive 下載工具",
    page_icon="📥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 設定日誌
setup_logging()
logger = get_logger(__name__)


def main():
    """主函數"""
    # 初始化 session state
    init_session_state()

    # 檢查認證狀態
    if not check_authentication():
        render_auth_page()
        return

    # 顯示性能提示（僅首次）
    if not SessionManager.get('performance_warning_shown'):
        SessionManager.set('performance_warning_shown', True)
        st.info("💡 **性能提示**：本應用已優化大型資料夾處理。如遇到卡頓，請使用「重新整理」或重新啟動應用程式。")

    # 渲染側邊欄
    render_sidebar()

    # 主要內容區域 - 分頁
    tab1, tab2, tab3 = st.tabs(["🌐 資料夾瀏覽", "📥 下載", "📋 任務管理"])

    with tab1:
        render_browser_page()

    with tab2:
        render_download_page()

    with tab3:
        render_tasks_page()


if __name__ == "__main__":
    main()
