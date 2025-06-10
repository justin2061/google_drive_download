"""
進度追蹤系統
提供下載進度監控和回調機制
"""

import time
import asyncio
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import threading
import json
from pathlib import Path

from ..utils.logger import LoggerMixin
from ..utils.helpers import format_size, format_time, format_speed, calculate_percentage


@dataclass
class ProgressSnapshot:
    """進度快照資料類別"""
    
    task_id: str
    timestamp: datetime
    downloaded_files: int
    total_files: int
    downloaded_bytes: int
    total_bytes: int
    current_speed: float  # bytes per second
    eta_seconds: Optional[float] = None
    status: str = 'downloading'
    current_file: Optional[str] = None
    error_count: int = 0
    
    @property
    def progress_percentage(self) -> float:
        """計算進度百分比"""
        if self.total_files == 0:
            return 0.0
        return calculate_percentage(self.downloaded_files, self.total_files)
    
    @property
    def bytes_percentage(self) -> float:
        """計算位元組進度百分比"""
        if self.total_bytes == 0:
            return 0.0
        return calculate_percentage(self.downloaded_bytes, self.total_bytes)
    
    @property
    def formatted_speed(self) -> str:
        """格式化速度"""
        return format_speed(self.current_speed)
    
    @property
    def formatted_eta(self) -> str:
        """格式化預估時間"""
        return format_time(self.eta_seconds)
    
    @property
    def formatted_downloaded_size(self) -> str:
        """格式化已下載大小"""
        return format_size(self.downloaded_bytes)
    
    @property
    def formatted_total_size(self) -> str:
        """格式化總大小"""
        return format_size(self.total_bytes)
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'task_id': self.task_id,
            'timestamp': self.timestamp.isoformat(),
            'downloaded_files': self.downloaded_files,
            'total_files': self.total_files,
            'downloaded_bytes': self.downloaded_bytes,
            'total_bytes': self.total_bytes,
            'current_speed': self.current_speed,
            'eta_seconds': self.eta_seconds,
            'status': self.status,
            'current_file': self.current_file,
            'error_count': self.error_count,
            'progress_percentage': self.progress_percentage,
            'bytes_percentage': self.bytes_percentage,
            'formatted_speed': self.formatted_speed,
            'formatted_eta': self.formatted_eta,
            'formatted_downloaded_size': self.formatted_downloaded_size,
            'formatted_total_size': self.formatted_total_size
        }


class ProgressTracker(LoggerMixin):
    """進度追蹤器
    
    負責追蹤下載進度、計算速度和預估時間
    """
    
    def __init__(self, task_id: str, update_interval: float = 1.0):
        self.task_id = task_id
        self.update_interval = update_interval
        
        # 進度資料
        self._downloaded_files = 0
        self._total_files = 0
        self._downloaded_bytes = 0
        self._total_bytes = 0
        self._current_file = None
        self._status = 'pending'
        self._error_count = 0
        
        # 速度計算
        self._speed_samples: List[tuple] = []  # (timestamp, bytes)
        self._speed_window = 10.0  # 速度計算視窗（秒）
        
        # 回調函數
        self._callbacks: List[Callable] = []
        
        # 控制
        self._running = False
        self._lock = threading.Lock()
        
        # 歷史記錄
        self._snapshots: List[ProgressSnapshot] = []
        self._max_snapshots = 1000
        
        self.logger.debug(f"進度追蹤器已初始化: {task_id}")
    
    def set_total(self, total_files: int, total_bytes: int = 0):
        """設定總數"""
        with self._lock:
            self._total_files = total_files
            self._total_bytes = total_bytes
            self.logger.debug(f"設定總數: {total_files} 檔案, {format_size(total_bytes)}")
    
    def update_file_progress(self, downloaded_files: int, current_file: str = None):
        """更新檔案進度"""
        with self._lock:
            self._downloaded_files = downloaded_files
            if current_file:
                self._current_file = current_file
            
            # 記錄速度樣本
            now = time.time()
            self._speed_samples.append((now, self._downloaded_bytes))
            
            # 清理舊樣本
            cutoff_time = now - self._speed_window
            self._speed_samples = [
                sample for sample in self._speed_samples 
                if sample[0] > cutoff_time
            ]
    
    def update_bytes_progress(self, downloaded_bytes: int):
        """更新位元組進度"""
        with self._lock:
            self._downloaded_bytes = downloaded_bytes
            
            # 記錄速度樣本
            now = time.time()
            self._speed_samples.append((now, downloaded_bytes))
            
            # 清理舊樣本
            cutoff_time = now - self._speed_window
            self._speed_samples = [
                sample for sample in self._speed_samples 
                if sample[0] > cutoff_time
            ]
    
    def increment_error(self):
        """增加錯誤計數"""
        with self._lock:
            self._error_count += 1
    
    def set_status(self, status: str):
        """設定狀態"""
        with self._lock:
            old_status = self._status
            self._status = status
            if old_status != status:
                self.logger.info(f"任務狀態變更: {old_status} -> {status}")
    
    def get_current_speed(self) -> float:
        """計算當前速度（bytes/sec）"""
        with self._lock:
            if len(self._speed_samples) < 2:
                return 0.0
            
            # 使用最近的樣本計算速度
            recent_samples = self._speed_samples[-10:]  # 最近10個樣本
            
            if len(recent_samples) < 2:
                return 0.0
            
            time_diff = recent_samples[-1][0] - recent_samples[0][0]
            bytes_diff = recent_samples[-1][1] - recent_samples[0][1]
            
            if time_diff <= 0:
                return 0.0
            
            return bytes_diff / time_diff
    
    def get_eta(self) -> Optional[float]:
        """計算預估剩餘時間（秒）"""
        with self._lock:
            if self._status not in ('downloading', 'processing'):
                return None
            
            current_speed = self.get_current_speed()
            
            if current_speed <= 0:
                return None
            
            # 優先使用位元組進度
            if self._total_bytes > 0:
                remaining_bytes = self._total_bytes - self._downloaded_bytes
                return remaining_bytes / current_speed
            
            # 退回到檔案進度估算
            if self._total_files > 0 and self._downloaded_files > 0:
                progress_ratio = self._downloaded_files / self._total_files
                if progress_ratio > 0:
                    elapsed_time = time.time() - (
                        self._speed_samples[0][0] if self._speed_samples else time.time()
                    )
                    total_estimated_time = elapsed_time / progress_ratio
                    return total_estimated_time - elapsed_time
            
            return None
    
    def get_snapshot(self) -> ProgressSnapshot:
        """取得當前進度快照"""
        with self._lock:
            return ProgressSnapshot(
                task_id=self.task_id,
                timestamp=datetime.now(),
                downloaded_files=self._downloaded_files,
                total_files=self._total_files,
                downloaded_bytes=self._downloaded_bytes,
                total_bytes=self._total_bytes,
                current_speed=self.get_current_speed(),
                eta_seconds=self.get_eta(),
                status=self._status,
                current_file=self._current_file,
                error_count=self._error_count
            )
    
    def add_callback(self, callback: Callable[[ProgressSnapshot], None]):
        """添加進度更新回調函數"""
        self._callbacks.append(callback)
        self.logger.debug(f"已添加進度回調函數: {callback.__name__}")
    
    def remove_callback(self, callback: Callable):
        """移除進度更新回調函數"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
            self.logger.debug(f"已移除進度回調函數: {callback.__name__}")
    
    def start_tracking(self):
        """開始進度追蹤"""
        if self._running:
            return
        
        self._running = True
        self.set_status('downloading')
        
        # 啟動追蹤執行緒
        tracking_thread = threading.Thread(target=self._tracking_loop, daemon=True)
        tracking_thread.start()
        
        self.logger.info(f"進度追蹤已開始: {self.task_id}")
    
    def stop_tracking(self):
        """停止進度追蹤"""
        self._running = False
        self.logger.info(f"進度追蹤已停止: {self.task_id}")
    
    def _tracking_loop(self):
        """追蹤迴圈"""
        while self._running:
            try:
                snapshot = self.get_snapshot()
                
                # 儲存快照
                self._save_snapshot(snapshot)
                
                # 呼叫回調函數
                for callback in self._callbacks:
                    try:
                        callback(snapshot)
                    except Exception as e:
                        self.logger.error(f"進度回調函數執行失敗: {e}")
                
                time.sleep(self.update_interval)
                
            except Exception as e:
                self.logger.error(f"進度追蹤迴圈錯誤: {e}")
                time.sleep(1.0)
    
    def _save_snapshot(self, snapshot: ProgressSnapshot):
        """儲存進度快照"""
        self._snapshots.append(snapshot)
        
        # 保持快照數量在限制內
        if len(self._snapshots) > self._max_snapshots:
            self._snapshots = self._snapshots[-self._max_snapshots:]
    
    def get_snapshots(self, limit: int = None) -> List[ProgressSnapshot]:
        """取得歷史快照"""
        if limit:
            return self._snapshots[-limit:]
        return self._snapshots.copy()
    
    def export_progress_data(self, filepath: str):
        """匯出進度資料"""
        try:
            data = {
                'task_id': self.task_id,
                'export_time': datetime.now().isoformat(),
                'snapshots': [snapshot.to_dict() for snapshot in self._snapshots]
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"進度資料已匯出: {filepath}")
            
        except Exception as e:
            self.logger.error(f"匯出進度資料失敗: {e}")
            raise


class ProgressManager(LoggerMixin):
    """進度管理器
    
    管理多個任務的進度追蹤
    """
    
    def __init__(self):
        self._trackers: Dict[str, ProgressTracker] = {}
        self._global_callbacks: List[Callable] = []
        self._lock = threading.Lock()
    
    def create_tracker(self, task_id: str, update_interval: float = 1.0) -> ProgressTracker:
        """建立進度追蹤器"""
        with self._lock:
            if task_id in self._trackers:
                self.logger.warning(f"進度追蹤器已存在: {task_id}")
                return self._trackers[task_id]
            
            tracker = ProgressTracker(task_id, update_interval)
            
            # 添加全域回調
            for callback in self._global_callbacks:
                tracker.add_callback(callback)
            
            self._trackers[task_id] = tracker
            self.logger.info(f"已建立進度追蹤器: {task_id}")
            
            return tracker
    
    def get_tracker(self, task_id: str) -> Optional[ProgressTracker]:
        """取得進度追蹤器"""
        return self._trackers.get(task_id)
    
    def remove_tracker(self, task_id: str):
        """移除進度追蹤器"""
        with self._lock:
            if task_id in self._trackers:
                tracker = self._trackers[task_id]
                tracker.stop_tracking()
                del self._trackers[task_id]
                self.logger.info(f"已移除進度追蹤器: {task_id}")
    
    def add_global_callback(self, callback: Callable):
        """添加全域進度回調"""
        self._global_callbacks.append(callback)
        
        # 為現有追蹤器添加回調
        for tracker in self._trackers.values():
            tracker.add_callback(callback)
        
        self.logger.debug(f"已添加全域進度回調: {callback.__name__}")
    
    def get_all_snapshots(self) -> Dict[str, ProgressSnapshot]:
        """取得所有任務的當前快照"""
        snapshots = {}
        for task_id, tracker in self._trackers.items():
            snapshots[task_id] = tracker.get_snapshot()
        return snapshots
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """取得總覽統計"""
        snapshots = self.get_all_snapshots()
        
        if not snapshots:
            return {
                'total_tasks': 0,
                'active_tasks': 0,
                'completed_tasks': 0,
                'failed_tasks': 0,
                'total_speed': 0,
                'total_downloaded': 0,
                'overall_progress': 0
            }
        
        total_tasks = len(snapshots)
        active_tasks = len([s for s in snapshots.values() if s.status == 'downloading'])
        completed_tasks = len([s for s in snapshots.values() if s.status == 'completed'])
        failed_tasks = len([s for s in snapshots.values() if s.status == 'failed'])
        
        total_speed = sum(s.current_speed for s in snapshots.values())
        total_downloaded = sum(s.downloaded_bytes for s in snapshots.values())
        
        # 計算整體進度
        total_files = sum(s.total_files for s in snapshots.values())
        downloaded_files = sum(s.downloaded_files for s in snapshots.values())
        overall_progress = (downloaded_files / total_files * 100) if total_files > 0 else 0
        
        return {
            'total_tasks': total_tasks,
            'active_tasks': active_tasks,
            'completed_tasks': completed_tasks,
            'failed_tasks': failed_tasks,
            'total_speed': total_speed,
            'total_downloaded': total_downloaded,
            'overall_progress': overall_progress
        }


# 全域進度管理器實例
progress_manager = ProgressManager() 