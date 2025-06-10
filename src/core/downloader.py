"""
非同步下載系統
提供高效能並發下載功能
"""

import asyncio
import aiofiles
import aiohttp
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Set
import uuid
import json

from ..utils.logger import LoggerMixin
from ..utils.config import get_config
from ..utils.exceptions import (
    DownloadError, 
    NetworkError, 
    FileNotFoundError,
    QuotaExceededError,
    RetryableError,
    FatalError,
    is_retryable_error,
    get_retry_delay
)
from ..utils.helpers import (
    create_directory_structure,
    extract_file_id_from_url,
    validate_file_id
)
from .progress import progress_manager, ProgressTracker
from .file_handler import file_handler
from .auth import ensure_authenticated


class DownloadStatus(Enum):
    """下載狀態枚舉"""
    PENDING = "pending"
    PREPARING = "preparing"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class DownloadTask:
    """下載任務資料類別"""
    
    id: str
    name: str
    source_url: str
    source_id: str
    output_path: Path
    status: DownloadStatus = DownloadStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    file_list: List[Dict[str, Any]] = field(default_factory=list)
    downloaded_files: List[str] = field(default_factory=list)
    failed_files: List[Dict[str, Any]] = field(default_factory=list)
    total_size: int = 0
    downloaded_size: int = 0
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = field(default_factory=lambda: get_config('download.max_retries', 3))
    max_concurrent: int = field(default_factory=lambda: get_config('download.max_concurrent', 5))
    preferred_format: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'id': self.id,
            'name': self.name,
            'source_url': self.source_url,
            'source_id': self.source_id,
            'output_path': str(self.output_path),
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'file_count': len(self.file_list),
            'downloaded_count': len(self.downloaded_files),
            'failed_count': len(self.failed_files),
            'total_size': self.total_size,
            'downloaded_size': self.downloaded_size,
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'max_concurrent': self.max_concurrent,
            'preferred_format': self.preferred_format
        }


class AsyncDownloader(LoggerMixin):
    """非同步下載器
    
    處理單個檔案的下載邏輯
    """
    
    def __init__(self, max_concurrent: int = None, chunk_size: int = None):
        self.max_concurrent = max_concurrent or get_config('download.max_concurrent', 5)
        self.chunk_size = chunk_size or get_config('download.chunk_size', 1048576)  # 1MB
        self.timeout = get_config('download.timeout', 300)  # 5 minutes
        
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        self._session: Optional[aiohttp.ClientSession] = None
        
        self.logger.info(f"非同步下載器已初始化 - 並發: {self.max_concurrent}, 分塊: {self.chunk_size}")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """取得 HTTP 會話"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=aiohttp.TCPConnector(limit=self.max_concurrent)
            )
        return self._session
    
    async def close(self):
        """關閉下載器"""
        if self._session and not self._session.closed:
            await self._session.close()
            self.logger.debug("HTTP 會話已關閉")
    
    async def download_file(self, 
                          file_info: Dict[str, Any], 
                          output_path: Path,
                          progress_tracker: ProgressTracker = None,
                          preferred_format: str = None) -> bool:
        """下載單個檔案
        
        Args:
            file_info: 檔案資訊
            output_path: 輸出路徑
            progress_tracker: 進度追蹤器
            preferred_format: 偏好格式
            
        Returns:
            下載是否成功
        """
        async with self._semaphore:
            file_id = file_info.get('id')
            file_name = file_info.get('name', 'unknown')
            
            try:
                self.logger.debug(f"開始下載檔案: {file_name}")
                
                # 使用執行緒池執行同步的 Google API 呼叫
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as executor:
                    # 下載檔案內容
                    content = await loop.run_in_executor(
                        executor,
                        file_handler.download_file_content,
                        file_id,
                        preferred_format
                    )
                    
                    # 生成安全檔案名稱
                    safe_filename = await loop.run_in_executor(
                        executor,
                        file_handler.generate_safe_filename,
                        file_info,
                        preferred_format
                    )
                
                # 建立完整檔案路徑
                file_path = output_path / safe_filename
                
                # 非同步寫入檔案
                await self._write_file_async(file_path, content)
                
                # 更新進度
                if progress_tracker:
                    current_files = progress_tracker._downloaded_files + 1
                    current_bytes = progress_tracker._downloaded_bytes + len(content)
                    
                    progress_tracker.update_file_progress(current_files, file_name)
                    progress_tracker.update_bytes_progress(current_bytes)
                
                self.logger.info(f"檔案下載完成: {safe_filename}")
                return True
                
            except Exception as e:
                if progress_tracker:
                    progress_tracker.increment_error()
                
                self.logger.error(f"下載檔案失敗 {file_name}: {e}")
                raise DownloadError(f"下載檔案失敗: {e}", file_id=file_id)
    
    async def _write_file_async(self, file_path: Path, content: bytes):
        """非同步寫入檔案"""
        try:
            # 確保目錄存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 非同步寫入
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
                
            self.logger.debug(f"檔案已寫入: {file_path}")
            
        except Exception as e:
            self.logger.error(f"寫入檔案失敗 {file_path}: {e}")
            raise
    
    async def download_multiple_files(self,
                                    file_list: List[Dict[str, Any]],
                                    output_path: Path,
                                    progress_tracker: ProgressTracker = None,
                                    preferred_format: str = None) -> Dict[str, Any]:
        """批次下載多個檔案
        
        Args:
            file_list: 檔案清單
            output_path: 輸出路徑
            progress_tracker: 進度追蹤器
            preferred_format: 偏好格式
            
        Returns:
            下載結果統計
        """
        if not file_list:
            return {'success': 0, 'failed': 0, 'total': 0}
        
        self.logger.info(f"開始批次下載 {len(file_list)} 個檔案")
        
        # 設定進度追蹤
        if progress_tracker:
            total_size = sum(
                int(f.get('size', 0)) for f in file_list 
                if f.get('size') and f['size'].isdigit()
            )
            progress_tracker.set_total(len(file_list), total_size)
            progress_tracker.start_tracking()
        
        success_count = 0
        failed_files = []
        
        # 建立下載任務
        download_tasks = []
        for file_info in file_list:
            # 跳過資料夾
            if file_info.get('mimeType') == 'application/vnd.google-apps.folder':
                continue
                
            task = self.download_file(
                file_info,
                output_path,
                progress_tracker,
                preferred_format
            )
            download_tasks.append((task, file_info))
        
        # 並發執行下載
        for task, file_info in download_tasks:
            try:
                await task
                success_count += 1
            except Exception as e:
                failed_files.append({
                    'file_info': file_info,
                    'error': str(e)
                })
                self.logger.warning(f"檔案下載失敗: {file_info.get('name')} - {e}")
        
        # 更新進度狀態
        if progress_tracker:
            if failed_files:
                progress_tracker.set_status('completed_with_errors')
            else:
                progress_tracker.set_status('completed')
        
        result = {
            'success': success_count,
            'failed': len(failed_files),
            'total': len(download_tasks),
            'failed_files': failed_files
        }
        
        self.logger.info(f"批次下載完成 - 成功: {success_count}, 失敗: {len(failed_files)}")
        return result


class DownloadManager(LoggerMixin):
    """下載管理器
    
    管理多個下載任務的生命週期
    """
    
    def __init__(self):
        self._tasks: Dict[str, DownloadTask] = {}
        self._active_downloads: Set[str] = set()
        self._downloaders: Dict[str, AsyncDownloader] = {}
        self._task_callbacks: List[Callable] = []
        
        # 執行緒池用於同步操作
        self._executor = ThreadPoolExecutor(max_workers=get_config('download.max_concurrent', 5))
        
        self.logger.info("下載管理器已初始化")
    
    def create_task(self,
                   source_url: str,
                   output_path: str,
                   name: str = None,
                   max_concurrent: int = None,
                   preferred_format: str = None) -> str:
        """建立下載任務
        
        Args:
            source_url: 來源 URL（Google Drive 連結或檔案 ID）
            output_path: 輸出路徑
            name: 任務名稱
            max_concurrent: 最大並發數
            preferred_format: 偏好格式
            
        Returns:
            任務 ID
        """
        # 提取檔案 ID
        source_id = extract_file_id_from_url(source_url)
        if not source_id:
            raise ValueError(f"無法從 URL 提取檔案 ID: {source_url}")
        
        if not validate_file_id(source_id):
            raise ValueError(f"無效的檔案 ID: {source_id}")
        
        # 生成任務 ID
        task_id = str(uuid.uuid4())
        
        # 建立任務
        task = DownloadTask(
            id=task_id,
            name=name or f"Download_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            source_url=source_url,
            source_id=source_id,
            output_path=Path(output_path),
            max_concurrent=max_concurrent or get_config('download.max_concurrent', 5),
            preferred_format=preferred_format
        )
        
        self._tasks[task_id] = task
        
        self.logger.info(f"建立下載任務: {task.name} ({task_id})")
        self._notify_task_update(task)
        
        return task_id
    
    async def start_task(self, task_id: str) -> bool:
        """開始執行下載任務
        
        Args:
            task_id: 任務 ID
            
        Returns:
            啟動是否成功
        """
        if task_id not in self._tasks:
            raise ValueError(f"任務不存在: {task_id}")
        
        task = self._tasks[task_id]
        
        if task.status != DownloadStatus.PENDING:
            self.logger.warning(f"任務 {task_id} 已經在執行或已完成")
            return False
        
        if task_id in self._active_downloads:
            self.logger.warning(f"任務 {task_id} 已在執行中")
            return False
        
        try:
            self.logger.info(f"開始執行下載任務: {task.name}")
            
            # 更新狀態
            task.status = DownloadStatus.PREPARING
            task.started_at = datetime.now()
            self._active_downloads.add(task_id)
            self._notify_task_update(task)
            
            # 建立進度追蹤器
            progress_tracker = progress_manager.create_tracker(task_id)
            
            # 建立下載器
            downloader = AsyncDownloader(
                max_concurrent=task.max_concurrent,
                chunk_size=get_config('download.chunk_size', 1048576)
            )
            self._downloaders[task_id] = downloader
            
            # 非同步執行下載
            asyncio.create_task(self._execute_download(task, progress_tracker, downloader))
            
            return True
            
        except Exception as e:
            self.logger.error(f"啟動下載任務失敗: {e}")
            task.status = DownloadStatus.FAILED
            task.error_message = str(e)
            self._active_downloads.discard(task_id)
            self._notify_task_update(task)
            return False
    
    async def _execute_download(self, 
                              task: DownloadTask, 
                              progress_tracker: ProgressTracker,
                              downloader: AsyncDownloader):
        """執行下載任務"""
        try:
            # 準備階段：取得檔案清單
            task.status = DownloadStatus.PREPARING
            self._notify_task_update(task)
            
            # 使用執行緒池執行同步的 API 呼叫
            loop = asyncio.get_event_loop()
            
            # 取得檔案資訊
            file_info = await loop.run_in_executor(
                self._executor,
                file_handler.get_file_info,
                task.source_id
            )
            
            # 檢查是檔案還是資料夾
            if file_info.get('mimeType') == 'application/vnd.google-apps.folder':
                # 資料夾：取得所有檔案
                file_list = await loop.run_in_executor(
                    self._executor,
                    file_handler.get_folder_contents,
                    task.source_id,
                    True  # recursive
                )
            else:
                # 單一檔案
                file_list = [file_info]
            
            # 篩選掉資料夾，只保留檔案
            files_to_download = [
                f for f in file_list 
                if f.get('mimeType') != 'application/vnd.google-apps.folder'
            ]
            
            task.file_list = files_to_download
            
            # 計算總大小
            task.total_size = sum(
                int(f.get('size', 0)) for f in files_to_download
                if f.get('size') and f['size'].isdigit()
            )
            
            self.logger.info(f"準備下載 {len(files_to_download)} 個檔案，總大小: {task.total_size} 位元組")
            
            # 建立輸出目錄
            if file_info.get('mimeType') == 'application/vnd.google-apps.folder':
                output_dir = create_directory_structure(
                    str(task.output_path.parent),
                    file_info.get('name', task.name)
                )
            else:
                output_dir = task.output_path.parent
                output_dir.mkdir(parents=True, exist_ok=True)
            
            # 開始下載
            task.status = DownloadStatus.DOWNLOADING
            self._notify_task_update(task)
            
            # 執行批次下載
            result = await downloader.download_multiple_files(
                files_to_download,
                output_dir,
                progress_tracker,
                task.preferred_format
            )
            
            # 更新任務結果
            task.downloaded_files = [f['id'] for f in files_to_download[:result['success']]]
            task.failed_files = result['failed_files']
            task.completed_at = datetime.now()
            
            if result['failed'] == 0:
                task.status = DownloadStatus.COMPLETED
                self.logger.info(f"下載任務完成: {task.name}")
            else:
                task.status = DownloadStatus.COMPLETED  # 部分成功也算完成
                self.logger.warning(f"下載任務部分完成: {task.name} - {result['failed']} 個檔案失敗")
            
        except Exception as e:
            self.logger.error(f"下載任務執行失敗: {e}")
            task.status = DownloadStatus.FAILED
            task.error_message = str(e)
            
            # 如果是可重試的錯誤，考慮重試
            if (is_retryable_error(e) and 
                task.retry_count < task.max_retries):
                
                task.retry_count += 1
                self.logger.info(f"準備重試任務: {task.name} (第 {task.retry_count} 次)")
                
                # 延遲重試
                retry_delay = get_retry_delay(e)
                await asyncio.sleep(retry_delay)
                
                # 重新開始
                task.status = DownloadStatus.PENDING
                await self.start_task(task.id)
                return
        
        finally:
            # 清理資源
            self._active_downloads.discard(task.id)
            if task.id in self._downloaders:
                await self._downloaders[task.id].close()
                del self._downloaders[task.id]
            
            progress_tracker.stop_tracking()
            self._notify_task_update(task)
    
    def pause_task(self, task_id: str) -> bool:
        """暫停下載任務"""
        if task_id not in self._tasks:
            return False
        
        task = self._tasks[task_id]
        if task.status != DownloadStatus.DOWNLOADING:
            return False
        
        task.status = DownloadStatus.PAUSED
        self._active_downloads.discard(task_id)
        
        # 停止進度追蹤
        tracker = progress_manager.get_tracker(task_id)
        if tracker:
            tracker.stop_tracking()
        
        self.logger.info(f"任務已暫停: {task.name}")
        self._notify_task_update(task)
        return True
    
    def cancel_task(self, task_id: str) -> bool:
        """取消下載任務"""
        if task_id not in self._tasks:
            return False
        
        task = self._tasks[task_id]
        task.status = DownloadStatus.CANCELLED
        self._active_downloads.discard(task_id)
        
        # 清理資源
        if task_id in self._downloaders:
            asyncio.create_task(self._downloaders[task_id].close())
            del self._downloaders[task_id]
        
        # 移除進度追蹤
        progress_manager.remove_tracker(task_id)
        
        self.logger.info(f"任務已取消: {task.name}")
        self._notify_task_update(task)
        return True
    
    def delete_task(self, task_id: str) -> bool:
        """刪除下載任務"""
        if task_id not in self._tasks:
            return False
        
        # 先取消任務
        self.cancel_task(task_id)
        
        # 從清單中移除
        del self._tasks[task_id]
        
        self.logger.info(f"任務已刪除: {task_id}")
        return True
    
    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        """取得任務資訊"""
        return self._tasks.get(task_id)
    
    def get_all_tasks(self) -> List[DownloadTask]:
        """取得所有任務"""
        return list(self._tasks.values())
    
    def get_tasks_by_status(self, status: DownloadStatus) -> List[DownloadTask]:
        """根據狀態取得任務"""
        return [task for task in self._tasks.values() if task.status == status]
    
    def add_task_callback(self, callback: Callable[[DownloadTask], None]):
        """添加任務狀態變更回調"""
        self._task_callbacks.append(callback)
    
    def _notify_task_update(self, task: DownloadTask):
        """通知任務狀態更新"""
        for callback in self._task_callbacks:
            try:
                callback(task)
            except Exception as e:
                self.logger.error(f"任務回調執行失敗: {e}")
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """取得總覽統計"""
        all_tasks = self.get_all_tasks()
        
        return {
            'total_tasks': len(all_tasks),
            'pending_tasks': len(self.get_tasks_by_status(DownloadStatus.PENDING)),
            'downloading_tasks': len(self.get_tasks_by_status(DownloadStatus.DOWNLOADING)),
            'completed_tasks': len(self.get_tasks_by_status(DownloadStatus.COMPLETED)),
            'failed_tasks': len(self.get_tasks_by_status(DownloadStatus.FAILED)),
            'active_downloads': len(self._active_downloads),
            'total_downloaded_size': sum(
                task.downloaded_size for task in all_tasks
                if task.status == DownloadStatus.COMPLETED
            )
        }
    
    async def cleanup(self):
        """清理資源"""
        # 關閉所有下載器
        for downloader in self._downloaders.values():
            await downloader.close()
        
        # 關閉執行緒池
        self._executor.shutdown(wait=True)
        
        self.logger.info("下載管理器已清理")


# 全域下載管理器實例
download_manager = DownloadManager() 