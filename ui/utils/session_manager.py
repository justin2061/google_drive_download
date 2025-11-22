"""
Session 狀態管理模組
統一管理 Streamlit session state
"""

import streamlit as st
from typing import Any, Optional
import sys
from pathlib import Path

# 添加專案根目錄到路徑
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.core.auth import AuthManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SessionManager:
    """Session 狀態管理器

    提供統一的 session state 管理接口
    """

    # 預設值定義
    DEFAULTS = {
        'authenticated': False,
        'user_info': None,
        'auto_refresh': False,
        'current_folder_id': None,
        'current_folder_name': "我的雲端硬碟",
        'folder_path': ["我的雲端硬碟"],
        'folder_id_path': [None],
        'show_download_options': False,
        'selected_folder_for_download': None,
        'show_folder_preview': False,
        'performance_warning_shown': False,
    }

    @classmethod
    def init_all(cls):
        """初始化所有 session state"""
        for key, default_value in cls.DEFAULTS.items():
            if key not in st.session_state:
                st.session_state[key] = default_value

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """取得 session state 值"""
        return st.session_state.get(key, default)

    @classmethod
    def set(cls, key: str, value: Any):
        """設定 session state 值"""
        st.session_state[key] = value

    @classmethod
    def reset(cls, key: str):
        """重設 session state 值為預設值"""
        if key in cls.DEFAULTS:
            st.session_state[key] = cls.DEFAULTS[key]

    @classmethod
    def reset_all(cls):
        """重設所有 session state 為預設值"""
        for key, default_value in cls.DEFAULTS.items():
            st.session_state[key] = default_value

    @classmethod
    def clear_folder_navigation(cls):
        """清除資料夾導航狀態"""
        cls.set('current_folder_id', None)
        cls.set('current_folder_name', "我的雲端硬碟")
        cls.set('folder_path', ["我的雲端硬碟"])
        cls.set('folder_id_path', [None])

    @classmethod
    def clear_download_state(cls):
        """清除下載相關狀態"""
        cls.set('show_download_options', False)
        cls.set('selected_folder_for_download', None)
        cls.set('show_folder_preview', False)

    @classmethod
    def navigate_to_folder(cls, folder_id: str, folder_name: str):
        """導航到指定資料夾"""
        cls.set('current_folder_id', folder_id)
        cls.set('current_folder_name', folder_name)

        # 更新路徑
        folder_path = cls.get('folder_path', [])
        folder_id_path = cls.get('folder_id_path', [])

        folder_path.append(folder_name)
        folder_id_path.append(folder_id)

        cls.set('folder_path', folder_path)
        cls.set('folder_id_path', folder_id_path)

    @classmethod
    def navigate_to_breadcrumb(cls, index: int):
        """導航到麵包屑指定位置"""
        folder_path = cls.get('folder_path', [])
        folder_id_path = cls.get('folder_id_path', [])

        if index < len(folder_path):
            cls.set('current_folder_id', folder_id_path[index])
            cls.set('current_folder_name', folder_path[index])
            cls.set('folder_path', folder_path[:index + 1])
            cls.set('folder_id_path', folder_id_path[:index + 1])

    @classmethod
    def navigate_up(cls):
        """導航到上層資料夾"""
        folder_path = cls.get('folder_path', [])
        folder_id_path = cls.get('folder_id_path', [])

        if len(folder_path) > 1:
            folder_path.pop()
            folder_id_path.pop()

            cls.set('folder_path', folder_path)
            cls.set('folder_id_path', folder_id_path)
            cls.set('current_folder_id', folder_id_path[-1])
            cls.set('current_folder_name', folder_path[-1])
            return True
        return False


def init_session_state():
    """初始化 session state（向後相容函數）"""
    SessionManager.init_all()


def get_auth_manager() -> AuthManager:
    """獲取 AuthManager 的單例"""
    if 'auth_manager' not in st.session_state:
        logger.info("在 session_state 中初始化 AuthManager")
        st.session_state.auth_manager = AuthManager()
    return st.session_state.auth_manager


def check_authentication() -> bool:
    """檢查認證狀態（不進行自動認證）"""
    auth_manager = get_auth_manager()

    try:
        if auth_manager.is_authenticated():
            if not SessionManager.get('authenticated'):
                SessionManager.set('authenticated', True)
                try:
                    SessionManager.set('user_info', auth_manager.get_user_info())
                except Exception as e:
                    logger.warning(f"取得用戶資訊失敗: {e}")
                    SessionManager.set('user_info', {
                        'email': 'Unknown',
                        'display_name': 'Unknown User',
                        'is_authenticated': True
                    })
            return True
        else:
            SessionManager.set('authenticated', False)
            SessionManager.set('user_info', None)
            return False
    except Exception as e:
        logger.error(f"檢查認證失敗: {e}")
        SessionManager.set('authenticated', False)
        SessionManager.set('user_info', None)
        return False


def logout():
    """登出並清理狀態"""
    auth_manager = get_auth_manager()
    auth_manager.logout()
    SessionManager.set('authenticated', False)
    SessionManager.set('user_info', None)
    SessionManager.clear_folder_navigation()
    SessionManager.clear_download_state()
