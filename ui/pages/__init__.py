"""UI 頁面模組"""

from .auth_page import render_auth_page
from .browser_page import render_browser_page
from .download_page import render_download_page
from .tasks_page import render_tasks_page

__all__ = [
    'render_auth_page',
    'render_browser_page',
    'render_download_page',
    'render_tasks_page'
]
