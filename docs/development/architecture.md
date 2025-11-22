# Google Drive 下載系統 - 技術架構與實作建議

## 1. 現狀分析總結

### 1.1 目前技術棧
- **語言**: Python 3.x
- **主要依賴**: Google API Client, OAuth 2.0, SQLite
- **開發工具**: Jupyter Notebook, py2exe
- **架構模式**: 單體應用，程序式編程

### 1.2 主要問題
1. **架構問題**: 程式碼散亂，缺乏模組化設計
2. **效能問題**: 單線程下載，效率低下
3. **維護問題**: 重複程式碼多，測試不足
4. **使用性問題**: 配置硬編碼，錯誤處理粗糙

## 2. 目標架構設計

### 2.1 整體架構願景

```
┌─────────────────────────────────────────────────────────┐
│                    使用者介面層                          │
├─────────────────┬─────────────────┬─────────────────────┤
│   命令列介面     │   Web 管理介面   │   RESTful API      │
│   (Click)       │   (React/Vue)   │   (FastAPI)        │
└─────────────────┴─────────────────┴─────────────────────┘
┌─────────────────────────────────────────────────────────┐
│                    應用服務層                            │
├─────────────────┬─────────────────┬─────────────────────┤
│   下載管理服務   │   檔案處理服務   │   進度追蹤服務      │
│   (Async)       │   (Converter)   │   (Progress)       │
└─────────────────┴─────────────────┴─────────────────────┘
┌─────────────────────────────────────────────────────────┐
│                    核心業務層                            │
├─────────────────┬─────────────────┬─────────────────────┤
│   身份驗證核心   │   下載引擎       │   任務調度器        │
│   (OAuth 2.0)   │   (AsyncIO)     │   (Queue)          │
└─────────────────┴─────────────────┴─────────────────────┘
┌─────────────────────────────────────────────────────────┐
│                    資料存取層                            │
├─────────────────┬─────────────────┬─────────────────────┤
│   資料庫存取     │   檔案系統       │   外部 API         │
│   (SQLAlchemy)  │   (aiofiles)    │   (Google Drive)   │
└─────────────────┴─────────────────┴─────────────────────┘
```

### 2.2 核心設計原則

1. **單一職責原則**: 每個模組只負責一個功能
2. **開放封閉原則**: 對擴展開放，對修改封閉
3. **依賴注入**: 降低模組間耦合度
4. **異步優先**: 提升 I/O 密集操作效能
5. **配置外部化**: 所有配置項目可外部調整

## 3. 詳細技術設計

### 3.1 身份驗證模組

```python
from abc import ABC, abstractmethod
from typing import Optional
import asyncio
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

class AuthProvider(ABC):
    """身份驗證提供者抽象基類"""
    
    @abstractmethod
    async def authenticate(self) -> Credentials:
        pass
    
    @abstractmethod
    async def refresh_token(self, credentials: Credentials) -> Credentials:
        pass

class GoogleOAuthProvider(AuthProvider):
    """Google OAuth 2.0 身份驗證提供者"""
    
    def __init__(self, config: dict):
        self.client_id = config['client_id']
        self.client_secret = config['client_secret']
        self.scopes = config['scopes']
        self.redirect_uri = config['redirect_uri']
        
    async def authenticate(self) -> Credentials:
        """執行 OAuth 2.0 認證流程"""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=self.scopes
        )
        flow.redirect_uri = self.redirect_uri
        
        # 實作認證邏輯
        # 返回認證憑證
        pass
    
    async def refresh_token(self, credentials: Credentials) -> Credentials:
        """刷新存取令牌"""
        if credentials.expired and credentials.refresh_token:
            await asyncio.to_thread(credentials.refresh, Request())
        return credentials
```

### 3.2 異步下載引擎

```python
import asyncio
import aiohttp
import aiofiles
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
from enum import Enum

class DownloadStatus(Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

@dataclass
class DownloadTask:
    file_id: str
    file_name: str
    file_size: Optional[int]
    mime_type: str
    output_path: str
    status: DownloadStatus = DownloadStatus.PENDING
    progress: float = 0.0
    error_message: Optional[str] = None
    retry_count: int = 0

class AsyncDownloader:
    """異步下載器"""
    
    def __init__(self, 
                 max_concurrent: int = 5,
                 chunk_size: int = 1024 * 1024,
                 max_retries: int = 3,
                 retry_delay: float = 1.0):
        self.max_concurrent = max_concurrent
        self.chunk_size = chunk_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.session: Optional[aiohttp.ClientSession] = None
        self.progress_callback: Optional[Callable] = None
```

### 3.3 進度追蹤系統

```python
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

@dataclass
class ProgressSnapshot:
    """進度快照"""
    timestamp: float
    completed_files: int
    total_files: int
    downloaded_size: int
    total_size: int
    current_speed: float
    average_speed: float
    eta_seconds: Optional[float]

class ProgressTracker:
    """進度追蹤器"""
    
    def __init__(self):
        self.total_files = 0
        self.completed_files = 0
        self.total_size = 0
        self.downloaded_size = 0
        self.start_time = time.time()
        self.callbacks: List[Callable] = []
        
    def get_snapshot(self) -> ProgressSnapshot:
        """取得當前進度快照"""
        current_time = time.time()
        elapsed_time = current_time - self.start_time
        
        # 計算平均速度和預估時間
        average_speed = self.downloaded_size / elapsed_time if elapsed_time > 0 else 0
        remaining_size = self.total_size - self.downloaded_size
        eta_seconds = remaining_size / average_speed if average_speed > 0 else None
        
        return ProgressSnapshot(
            timestamp=current_time,
            completed_files=self.completed_files,
            total_files=self.total_files,
            downloaded_size=self.downloaded_size,
            total_size=self.total_size,
            current_speed=average_speed,
            average_speed=average_speed,
            eta_seconds=eta_seconds
        )
```

### 3.4 配置管理系統

```python
import yaml
from pathlib import Path
from typing import Dict, Any

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self._load_config()
    
    def _create_default_config(self):
        """建立預設配置檔案"""
        default_config = {
            'download': {
                'max_concurrent': 5,
                'chunk_size': 1048576,
                'output_directory': './downloads',
                'max_retries': 3
            },
            'auth': {
                'credentials_file': 'credentials.json',
                'token_file': 'token.pickle',
                'scopes': [
                    'https://www.googleapis.com/auth/drive.readonly'
                ]
            },
            'logging': {
                'level': 'INFO',
                'file': 'app.log',
                'max_size': 10485760,
                'backup_count': 5
            }
        }
        
        self._config = default_config
        self.save_config()
    
    def get(self, key: str, default: Any = None) -> Any:
        """取得配置值"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
```

## 4. 實作建議與最佳實踐

### 4.1 異步程式設計模式

```python
# 使用 async/await 模式
async def main():
    async with AsyncDownloader() as downloader:
        tasks = await create_download_tasks()
        await downloader.download_multiple_files(tasks)

# 使用上下文管理器確保資源清理
class DatabaseManager:
    async def __aenter__(self):
        self.connection = await create_connection()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.connection.close()
```

### 4.2 錯誤處理策略

```python
# 分層錯誤處理
class DownloadException(Exception):
    """下載相關例外基類"""
    pass

class NetworkException(DownloadException):
    """網路相關例外"""
    pass

class AuthenticationException(DownloadException):
    """認證相關例外"""
    pass
```

### 4.3 測試策略

```python
import pytest
from unittest.mock import AsyncMock, Mock

@pytest.mark.asyncio
async def test_download_file_success():
    # Arrange
    downloader = AsyncDownloader(max_concurrent=1)
    task = DownloadTask(
        file_id="test_id",
        file_name="test.txt",
        mime_type="text/plain",
        output_path="/tmp/test.txt"
    )
    
    # Mock dependencies
    mock_session = AsyncMock()
    downloader.session = mock_session
    
    # Act
    result = await downloader.download_file(task, Mock())
    
    # Assert
    assert result.status == DownloadStatus.COMPLETED
```

### 4.4 效能最佳化建議

1. **連線池使用**
```python
connector = aiohttp.TCPConnector(
    limit=100,           # 總連線數限制
    limit_per_host=30,   # 每個主機連線數限制
    keepalive_timeout=30 # 保持連線時間
)
```

2. **記憶體管理**
```python
async def stream_download(url: str):
    async with session.get(url) as response:
        async for chunk in response.content.iter_chunked(8192):
            yield chunk
```

## 5. 部署與維運建議

### 5.1 容器化部署

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY config.yaml .

CMD ["python", "-m", "src.cli.main"]
```

### 5.2 監控與日誌

```python
import structlog

logger = structlog.get_logger()

logger.info(
    "Download completed",
    file_id=task.file_id,
    file_size=task.file_size,
    duration=duration,
    success=True
)
```

### 5.3 健康檢查

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "active_downloads": len(download_manager.active_downloads)
    }
```

---
*這份技術架構文檔提供了詳細的實作指導，可以作為重構和開發的技術參考。建議按照優先順序逐步實作，確保每個階段都有充分的測試覆蓋。* 