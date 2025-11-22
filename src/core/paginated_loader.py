"""
分頁資料夾載入器
提供大型資料夾的增量載入功能，防止 UI 凍結
"""

import time
from typing import List, Dict, Any, Optional, Generator, Callable
from dataclasses import dataclass, field
from enum import Enum

from googleapiclient.errors import HttpError

from ..utils.logger import LoggerMixin
from ..utils.exceptions import (
    FileNotFoundError,
    FilePermissionError,
    NetworkError,
    ValidationError
)
from ..utils.helpers import validate_file_id
from .auth import get_authenticated_service, ensure_authenticated
from .retry_manager import RetryManager, RetryStrategy


class LoadingStatus(Enum):
    """載入狀態"""
    IDLE = "idle"           # 閒置
    LOADING = "loading"     # 載入中
    COMPLETED = "completed" # 已完成
    ERROR = "error"         # 發生錯誤


@dataclass
class PageResult:
    """分頁結果"""
    items: List[Dict[str, Any]]
    page_number: int
    has_more: bool
    total_loaded: int
    error: Optional[str] = None

    def __bool__(self):
        return self.error is None


@dataclass
class LoaderState:
    """載入器狀態"""
    status: LoadingStatus = LoadingStatus.IDLE
    total_items: int = 0
    total_pages: int = 0
    current_page: int = 0
    has_more: bool = True
    error_message: Optional[str] = None
    last_load_time: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'status': self.status.value,
            'total_items': self.total_items,
            'total_pages': self.total_pages,
            'current_page': self.current_page,
            'has_more': self.has_more,
            'error_message': self.error_message,
            'last_load_time': self.last_load_time
        }


class PaginatedFolderLoader(LoggerMixin):
    """分頁資料夾載入器

    用於大型資料夾的增量載入，避免 UI 凍結

    使用方式:
        loader = PaginatedFolderLoader(folder_id='xxx', page_size=50)

        # 載入第一頁
        result = loader.load_next_page()

        # 檢查是否有更多
        while loader.has_more():
            result = loader.load_next_page()
            # 處理 result.items
    """

    # 預設欄位（用於列表顯示）
    DEFAULT_FIELDS = 'id,name,mimeType,size,modifiedTime,createdTime'

    # 完整欄位（用於詳細資訊）
    FULL_FIELDS = 'id,name,mimeType,size,modifiedTime,createdTime,parents,webViewLink,thumbnailLink'

    def __init__(
        self,
        folder_id: str,
        page_size: int = 50,
        fields: str = None,
        order_by: str = 'folder,name',
        include_trashed: bool = False,
        drive_service = None
    ):
        """初始化分頁載入器

        Args:
            folder_id: 資料夾 ID
            page_size: 每頁項目數（建議 20-100）
            fields: 要取得的欄位
            order_by: 排序方式
            include_trashed: 是否包含已刪除的檔案
            drive_service: Drive 服務實例（可選）
        """
        if not validate_file_id(folder_id):
            raise ValidationError('folder_id', folder_id, "無效的資料夾 ID 格式")

        self.folder_id = folder_id
        self.page_size = min(max(page_size, 10), 100)  # 限制在 10-100 之間
        self.fields = fields or self.DEFAULT_FIELDS
        self.order_by = order_by
        self.include_trashed = include_trashed
        self._drive_service = drive_service

        # 狀態管理
        self._state = LoaderState()
        self._page_token: Optional[str] = None
        self._all_items: List[Dict[str, Any]] = []
        self._folder_info: Optional[Dict[str, Any]] = None

        # 重試管理器
        self._retry_manager = RetryManager(
            max_retries=3,
            base_delay=1.0,
            max_delay=30.0,
            strategy=RetryStrategy.EXPONENTIAL
        )

        self.logger.debug(f"分頁載入器已初始化 - 資料夾: {folder_id}, 每頁: {page_size}")

    @property
    def drive_service(self):
        """取得 Drive 服務實例"""
        if self._drive_service is None:
            self._drive_service = get_authenticated_service('drive')
        return self._drive_service

    @property
    def state(self) -> LoaderState:
        """取得當前狀態"""
        return self._state

    @property
    def folder_info(self) -> Optional[Dict[str, Any]]:
        """取得資料夾資訊"""
        return self._folder_info

    @property
    def items(self) -> List[Dict[str, Any]]:
        """取得所有已載入的項目"""
        return self._all_items.copy()

    def has_more(self) -> bool:
        """是否有更多頁面"""
        return self._state.has_more

    def is_loading(self) -> bool:
        """是否正在載入"""
        return self._state.status == LoadingStatus.LOADING

    def is_completed(self) -> bool:
        """是否已完成載入"""
        return self._state.status == LoadingStatus.COMPLETED

    def get_progress(self) -> float:
        """取得載入進度（0-1）

        注意：這是估算值，因為無法提前知道總數
        """
        if self._state.status == LoadingStatus.COMPLETED:
            return 1.0
        if self._state.total_items == 0:
            return 0.0
        # 基於是否還有更多頁面來估算
        if self._state.has_more:
            return 0.5 + (self._state.current_page * 0.1)  # 最多顯示到 90%
        return 1.0

    def _validate_folder(self) -> bool:
        """驗證資料夾存在且可存取"""
        if self._folder_info is not None:
            return True

        try:
            result = self.drive_service.files().get(
                fileId=self.folder_id,
                fields='id,name,mimeType'
            ).execute()

            if result.get('mimeType') != 'application/vnd.google-apps.folder':
                raise ValidationError('folder_id', self.folder_id, "指定的 ID 不是資料夾")

            self._folder_info = result
            return True

        except HttpError as e:
            if e.resp.status == 404:
                raise FileNotFoundError(self.folder_id, "資料夾不存在")
            elif e.resp.status == 403:
                raise FilePermissionError(self.folder_id, "沒有資料夾存取權限")
            raise NetworkError(f"HTTP 錯誤: {e}", status_code=e.resp.status)

    def load_next_page(self) -> PageResult:
        """載入下一頁

        Returns:
            PageResult 物件，包含載入的項目和狀態
        """
        # 檢查是否還有更多頁面
        if not self._state.has_more:
            return PageResult(
                items=[],
                page_number=self._state.current_page,
                has_more=False,
                total_loaded=self._state.total_items
            )

        # 更新狀態為載入中
        self._state.status = LoadingStatus.LOADING
        start_time = time.time()

        try:
            # 首次載入時驗證資料夾
            if self._state.current_page == 0:
                self._validate_folder()

            # 建立查詢
            query = f"'{self.folder_id}' in parents"
            if not self.include_trashed:
                query += " and trashed=false"

            # API 呼叫
            def api_call():
                return self.drive_service.files().list(
                    q=query,
                    pageSize=self.page_size,
                    pageToken=self._page_token,
                    orderBy=self.order_by,
                    fields=f'nextPageToken,files({self.fields})'
                ).execute()

            # 使用重試機制執行 API 呼叫
            retry_result = self._retry_manager.retry_sync(api_call)

            if not retry_result.success:
                raise retry_result.error

            results = retry_result.result
            items = results.get('files', [])
            self._page_token = results.get('nextPageToken')

            # 更新狀態
            self._state.current_page += 1
            self._state.total_items += len(items)
            self._state.total_pages = self._state.current_page
            self._state.has_more = self._page_token is not None
            self._state.last_load_time = time.time() - start_time

            # 如果沒有更多頁面，標記為完成
            if not self._state.has_more:
                self._state.status = LoadingStatus.COMPLETED
            else:
                self._state.status = LoadingStatus.IDLE

            # 儲存項目
            self._all_items.extend(items)

            self.logger.info(
                f"載入第 {self._state.current_page} 頁: {len(items)} 個項目, "
                f"總計 {self._state.total_items} 個, "
                f"耗時 {self._state.last_load_time:.2f}s"
            )

            return PageResult(
                items=items,
                page_number=self._state.current_page,
                has_more=self._state.has_more,
                total_loaded=self._state.total_items
            )

        except Exception as e:
            self._state.status = LoadingStatus.ERROR
            self._state.error_message = str(e)
            self.logger.error(f"載入分頁失敗: {e}")

            return PageResult(
                items=[],
                page_number=self._state.current_page,
                has_more=False,
                total_loaded=self._state.total_items,
                error=str(e)
            )

    def load_all(
        self,
        max_pages: int = None,
        progress_callback: Callable[[int, int], None] = None
    ) -> List[Dict[str, Any]]:
        """載入所有頁面

        Args:
            max_pages: 最大頁數限制（防止無限載入）
            progress_callback: 進度回調函數，接收 (current_page, total_items)

        Returns:
            所有載入的項目清單
        """
        max_pages = max_pages or 100  # 預設最多 100 頁

        while self.has_more() and self._state.current_page < max_pages:
            result = self.load_next_page()

            if not result:
                self.logger.error(f"載入失敗: {result.error}")
                break

            if progress_callback:
                progress_callback(self._state.current_page, self._state.total_items)

            # 短暫延遲，避免過快請求
            if self.has_more():
                time.sleep(0.2)

        return self._all_items

    def load_pages_generator(
        self,
        max_pages: int = None
    ) -> Generator[PageResult, None, None]:
        """產生器模式載入頁面

        Args:
            max_pages: 最大頁數限制

        Yields:
            PageResult 物件
        """
        max_pages = max_pages or 100

        while self.has_more() and self._state.current_page < max_pages:
            result = self.load_next_page()
            yield result

            if not result or not result.has_more:
                break

            # 短暫延遲
            time.sleep(0.2)

    def reset(self):
        """重置載入器狀態"""
        self._state = LoaderState()
        self._page_token = None
        self._all_items = []
        self.logger.debug("載入器已重置")

    def get_statistics(self) -> Dict[str, Any]:
        """取得載入統計資訊"""
        folders = sum(1 for item in self._all_items
                     if item.get('mimeType') == 'application/vnd.google-apps.folder')
        files = len(self._all_items) - folders

        total_size = 0
        for item in self._all_items:
            size = item.get('size')
            if size:
                try:
                    total_size += int(size)
                except (ValueError, TypeError):
                    pass

        return {
            'folder_id': self.folder_id,
            'folder_name': self._folder_info.get('name') if self._folder_info else None,
            'total_items': self._state.total_items,
            'total_folders': folders,
            'total_files': files,
            'total_size_bytes': total_size,
            'pages_loaded': self._state.total_pages,
            'is_complete': self._state.status == LoadingStatus.COMPLETED,
            'has_more': self._state.has_more
        }


class CachedFolderLoader(LoggerMixin):
    """帶快取的資料夾載入器

    在分頁載入基礎上增加快取功能
    """

    def __init__(self, cache_ttl: int = 300):
        """初始化快取載入器

        Args:
            cache_ttl: 快取有效時間（秒），預設 5 分鐘
        """
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.logger.debug(f"快取載入器已初始化，TTL: {cache_ttl}s")

    def get_loader(
        self,
        folder_id: str,
        page_size: int = 50,
        force_refresh: bool = False
    ) -> PaginatedFolderLoader:
        """取得或建立載入器

        Args:
            folder_id: 資料夾 ID
            page_size: 每頁大小
            force_refresh: 是否強制重新建立

        Returns:
            PaginatedFolderLoader 實例
        """
        cache_key = f"{folder_id}:{page_size}"
        current_time = time.time()

        # 檢查快取
        if not force_refresh and cache_key in self._cache:
            cached = self._cache[cache_key]
            if current_time - cached['created_at'] < self.cache_ttl:
                self.logger.debug(f"使用快取的載入器: {folder_id}")
                return cached['loader']

        # 建立新的載入器
        loader = PaginatedFolderLoader(folder_id, page_size)
        self._cache[cache_key] = {
            'loader': loader,
            'created_at': current_time
        }

        self.logger.debug(f"建立新的載入器: {folder_id}")
        return loader

    def get_cached_items(self, folder_id: str) -> Optional[List[Dict[str, Any]]]:
        """取得快取的項目（如果有）

        Args:
            folder_id: 資料夾 ID

        Returns:
            快取的項目清單，如果沒有則返回 None
        """
        for cache_key, cached in self._cache.items():
            if cache_key.startswith(folder_id):
                current_time = time.time()
                if current_time - cached['created_at'] < self.cache_ttl:
                    loader = cached['loader']
                    if loader.items:
                        return loader.items
        return None

    def invalidate(self, folder_id: str = None):
        """使快取失效

        Args:
            folder_id: 要失效的資料夾 ID，如果為 None 則清除所有快取
        """
        if folder_id is None:
            self._cache.clear()
            self.logger.debug("已清除所有快取")
        else:
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(folder_id)]
            for key in keys_to_remove:
                del self._cache[key]
            self.logger.debug(f"已清除資料夾快取: {folder_id}")

    def cleanup_expired(self):
        """清理過期的快取"""
        current_time = time.time()
        expired_keys = [
            k for k, v in self._cache.items()
            if current_time - v['created_at'] >= self.cache_ttl
        ]
        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            self.logger.debug(f"已清理 {len(expired_keys)} 個過期快取")


# 全域快取載入器實例
folder_loader_cache = CachedFolderLoader()


def load_folder_paginated(
    folder_id: str,
    page_size: int = 50,
    use_cache: bool = True
) -> PaginatedFolderLoader:
    """便捷函數：載入資料夾（分頁模式）

    Args:
        folder_id: 資料夾 ID
        page_size: 每頁大小
        use_cache: 是否使用快取

    Returns:
        PaginatedFolderLoader 實例
    """
    if use_cache:
        return folder_loader_cache.get_loader(folder_id, page_size)
    return PaginatedFolderLoader(folder_id, page_size)
