"""
分頁資料夾載入器測試
"""

import pytest
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

sys.path.append(str(Path(__file__).parent.parent))

from src.core.paginated_loader import (
    PaginatedFolderLoader,
    CachedFolderLoader,
    LoadingStatus,
    PageResult,
    LoaderState,
    load_folder_paginated,
    folder_loader_cache
)
from src.utils.exceptions import (
    FileNotFoundError,
    FilePermissionError,
    ValidationError
)


class TestLoadingStatus:
    """測試載入狀態枚舉"""

    def test_status_values(self):
        """測試狀態值"""
        assert LoadingStatus.IDLE.value == "idle"
        assert LoadingStatus.LOADING.value == "loading"
        assert LoadingStatus.COMPLETED.value == "completed"
        assert LoadingStatus.ERROR.value == "error"


class TestPageResult:
    """測試分頁結果"""

    def test_success_result(self):
        """測試成功結果"""
        items = [{'id': '1', 'name': 'file1'}]
        result = PageResult(
            items=items,
            page_number=1,
            has_more=True,
            total_loaded=1
        )

        assert result.items == items
        assert result.page_number == 1
        assert result.has_more is True
        assert result.total_loaded == 1
        assert result.error is None
        assert bool(result) is True

    def test_error_result(self):
        """測試錯誤結果"""
        result = PageResult(
            items=[],
            page_number=0,
            has_more=False,
            total_loaded=0,
            error="Connection failed"
        )

        assert result.error == "Connection failed"
        assert bool(result) is False


class TestLoaderState:
    """測試載入器狀態"""

    def test_default_state(self):
        """測試預設狀態"""
        state = LoaderState()

        assert state.status == LoadingStatus.IDLE
        assert state.total_items == 0
        assert state.total_pages == 0
        assert state.current_page == 0
        assert state.has_more is True
        assert state.error_message is None

    def test_to_dict(self):
        """測試轉換為字典"""
        state = LoaderState(
            status=LoadingStatus.LOADING,
            total_items=50,
            total_pages=1,
            current_page=1
        )

        result = state.to_dict()

        assert result['status'] == 'loading'
        assert result['total_items'] == 50
        assert result['total_pages'] == 1


class TestPaginatedFolderLoader:
    """測試分頁資料夾載入器"""

    def setup_method(self):
        """測試前設定"""
        self.mock_drive_service = Mock()

    def test_init_invalid_folder_id(self):
        """測試初始化 - 無效資料夾 ID"""
        with pytest.raises(ValidationError):
            PaginatedFolderLoader(folder_id="", page_size=50)

    def test_init_valid_folder_id(self):
        """測試初始化 - 有效資料夾 ID"""
        loader = PaginatedFolderLoader(
            folder_id="valid_folder_id_123",
            page_size=50,
            drive_service=self.mock_drive_service
        )

        assert loader.folder_id == "valid_folder_id_123"
        assert loader.page_size == 50

    def test_page_size_min_limit(self):
        """測試頁面大小最小限制"""
        loader = PaginatedFolderLoader(
            folder_id="valid_folder_id_123",
            page_size=5,  # 小於最小值 10
            drive_service=self.mock_drive_service
        )

        assert loader.page_size == 10

    def test_page_size_max_limit(self):
        """測試頁面大小最大限制"""
        loader = PaginatedFolderLoader(
            folder_id="valid_folder_id_123",
            page_size=200,  # 大於最大值 100
            drive_service=self.mock_drive_service
        )

        assert loader.page_size == 100

    def test_initial_state(self):
        """測試初始狀態"""
        loader = PaginatedFolderLoader(
            folder_id="valid_folder_id_123",
            drive_service=self.mock_drive_service
        )

        assert loader.state.status == LoadingStatus.IDLE
        assert loader.has_more() is True
        assert loader.is_loading() is False
        assert loader.is_completed() is False
        assert loader.items == []

    def test_get_progress_initial(self):
        """測試初始進度"""
        loader = PaginatedFolderLoader(
            folder_id="valid_folder_id_123",
            drive_service=self.mock_drive_service
        )

        assert loader.get_progress() == 0.0

    @patch('src.core.paginated_loader.get_authenticated_service')
    def test_load_next_page_no_more(self, mock_get_service):
        """測試載入下一頁 - 沒有更多頁面"""
        loader = PaginatedFolderLoader(
            folder_id="valid_folder_id_123",
            drive_service=self.mock_drive_service
        )
        loader._state.has_more = False

        result = loader.load_next_page()

        assert result.items == []
        assert result.has_more is False

    def test_reset(self):
        """測試重置"""
        loader = PaginatedFolderLoader(
            folder_id="valid_folder_id_123",
            drive_service=self.mock_drive_service
        )

        # 模擬已載入一些資料
        loader._state.total_items = 50
        loader._state.current_page = 2
        loader._all_items = [{'id': '1'}]

        loader.reset()

        assert loader.state.total_items == 0
        assert loader.state.current_page == 0
        assert loader.items == []

    def test_get_statistics_empty(self):
        """測試統計資訊 - 空"""
        loader = PaginatedFolderLoader(
            folder_id="valid_folder_id_123",
            drive_service=self.mock_drive_service
        )

        stats = loader.get_statistics()

        assert stats['folder_id'] == "valid_folder_id_123"
        assert stats['total_items'] == 0
        assert stats['total_folders'] == 0
        assert stats['total_files'] == 0
        assert stats['is_complete'] is False

    def test_get_statistics_with_items(self):
        """測試統計資訊 - 有項目"""
        loader = PaginatedFolderLoader(
            folder_id="valid_folder_id_123",
            drive_service=self.mock_drive_service
        )

        # 模擬已載入的項目
        loader._all_items = [
            {'id': '1', 'mimeType': 'application/vnd.google-apps.folder'},
            {'id': '2', 'mimeType': 'text/plain', 'size': '1024'},
            {'id': '3', 'mimeType': 'image/png', 'size': '2048'},
        ]
        loader._state.total_items = 3

        stats = loader.get_statistics()

        assert stats['total_items'] == 3
        assert stats['total_folders'] == 1
        assert stats['total_files'] == 2
        assert stats['total_size_bytes'] == 3072


class TestCachedFolderLoader:
    """測試帶快取的資料夾載入器"""

    def setup_method(self):
        """測試前設定"""
        self.cache_loader = CachedFolderLoader(cache_ttl=60)

    def test_init(self):
        """測試初始化"""
        loader = CachedFolderLoader(cache_ttl=300)

        assert loader.cache_ttl == 300

    @patch('src.core.paginated_loader.PaginatedFolderLoader')
    def test_get_loader_creates_new(self, mock_loader_class):
        """測試取得載入器 - 建立新的"""
        mock_loader = Mock()
        mock_loader_class.return_value = mock_loader

        result = self.cache_loader.get_loader("folder_123", page_size=50)

        assert result == mock_loader
        mock_loader_class.assert_called_once_with("folder_123", 50)

    @patch('src.core.paginated_loader.PaginatedFolderLoader')
    def test_get_loader_uses_cache(self, mock_loader_class):
        """測試取得載入器 - 使用快取"""
        mock_loader = Mock()
        mock_loader_class.return_value = mock_loader

        # 第一次呼叫
        result1 = self.cache_loader.get_loader("folder_123", page_size=50)
        # 第二次呼叫應該使用快取
        result2 = self.cache_loader.get_loader("folder_123", page_size=50)

        assert result1 == result2
        assert mock_loader_class.call_count == 1  # 只呼叫一次

    @patch('src.core.paginated_loader.PaginatedFolderLoader')
    def test_get_loader_force_refresh(self, mock_loader_class):
        """測試取得載入器 - 強制重新建立"""
        mock_loader = Mock()
        mock_loader_class.return_value = mock_loader

        # 第一次呼叫
        self.cache_loader.get_loader("folder_123", page_size=50)
        # 強制重新建立
        self.cache_loader.get_loader("folder_123", page_size=50, force_refresh=True)

        assert mock_loader_class.call_count == 2

    def test_get_cached_items_none(self):
        """測試取得快取項目 - 無快取"""
        result = self.cache_loader.get_cached_items("folder_123")

        assert result is None

    @patch('src.core.paginated_loader.PaginatedFolderLoader')
    def test_get_cached_items_exists(self, mock_loader_class):
        """測試取得快取項目 - 有快取"""
        mock_loader = Mock()
        mock_loader.items = [{'id': '1', 'name': 'file1'}]
        mock_loader_class.return_value = mock_loader

        # 建立快取
        self.cache_loader.get_loader("folder_123", page_size=50)

        # 取得快取項目
        result = self.cache_loader.get_cached_items("folder_123")

        assert result == [{'id': '1', 'name': 'file1'}]

    def test_invalidate_all(self):
        """測試使所有快取失效"""
        # 建立一些快取
        self.cache_loader._cache['folder_123:50'] = {
            'loader': Mock(),
            'created_at': time.time()
        }
        self.cache_loader._cache['folder_456:50'] = {
            'loader': Mock(),
            'created_at': time.time()
        }

        self.cache_loader.invalidate()

        assert len(self.cache_loader._cache) == 0

    def test_invalidate_specific_folder(self):
        """測試使特定資料夾快取失效"""
        # 建立一些快取
        self.cache_loader._cache['folder_123:50'] = {
            'loader': Mock(),
            'created_at': time.time()
        }
        self.cache_loader._cache['folder_456:50'] = {
            'loader': Mock(),
            'created_at': time.time()
        }

        self.cache_loader.invalidate("folder_123")

        assert 'folder_123:50' not in self.cache_loader._cache
        assert 'folder_456:50' in self.cache_loader._cache

    def test_cleanup_expired(self):
        """測試清理過期快取"""
        # 建立過期的快取
        self.cache_loader._cache['folder_old:50'] = {
            'loader': Mock(),
            'created_at': time.time() - 100  # 100 秒前
        }
        # 建立新的快取
        self.cache_loader._cache['folder_new:50'] = {
            'loader': Mock(),
            'created_at': time.time()
        }

        self.cache_loader.cleanup_expired()

        assert 'folder_old:50' not in self.cache_loader._cache
        assert 'folder_new:50' in self.cache_loader._cache


class TestLoadFolderPaginated:
    """測試便捷函數"""

    @patch('src.core.paginated_loader.folder_loader_cache')
    def test_load_with_cache(self, mock_cache):
        """測試使用快取載入"""
        mock_loader = Mock()
        mock_cache.get_loader.return_value = mock_loader

        result = load_folder_paginated("folder_123", page_size=50, use_cache=True)

        assert result == mock_loader
        mock_cache.get_loader.assert_called_once_with("folder_123", 50)

    @patch('src.core.paginated_loader.PaginatedFolderLoader')
    def test_load_without_cache(self, mock_loader_class):
        """測試不使用快取載入"""
        mock_loader = Mock()
        mock_loader_class.return_value = mock_loader

        result = load_folder_paginated("folder_123", page_size=50, use_cache=False)

        assert result == mock_loader
        mock_loader_class.assert_called_once_with("folder_123", 50)


class TestGlobalFolderLoaderCache:
    """測試全域快取載入器實例"""

    def test_global_cache_exists(self):
        """測試全域實例存在"""
        assert folder_loader_cache is not None
        assert isinstance(folder_loader_cache, CachedFolderLoader)


if __name__ == '__main__':
    pytest.main([__file__])
