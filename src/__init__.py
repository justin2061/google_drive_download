"""
Google Drive 下載系統
~~~~~~~~~~~~~~~~~~~~~

一個現代化的 Google Drive 檔案下載工具，支援並發下載、進度追蹤和 Web 管理介面。

:copyright: (c) 2024
:license: MIT
"""

__version__ = '2.0.0'
__author__ = 'Google Drive Downloader Team'

from .core.auth import AuthManager, GoogleOAuthProvider
from .core.downloader import AsyncDownloader, DownloadManager
from .core.progress import ProgressTracker
from .utils.config import ConfigManager

__all__ = [
    'AuthManager',
    'GoogleOAuthProvider', 
    'AsyncDownloader',
    'DownloadManager',
    'ProgressTracker',
    'ConfigManager'
] 