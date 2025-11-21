"""
Pydantic 配置模型
提供型別安全和驗證的配置管理
"""

from typing import List, Optional, Any, Dict
from pathlib import Path

try:
    from pydantic import BaseModel, Field, field_validator, model_validator
    from pydantic_settings import BaseSettings
    PYDANTIC_V2 = True
except ImportError:
    # Fallback for pydantic v1
    from pydantic import BaseModel, Field, validator, root_validator
    PYDANTIC_V2 = False


class DownloadConfig(BaseModel):
    """下載配置"""

    max_concurrent: int = Field(
        default=5,
        ge=1,
        le=20,
        description="最大並發下載數"
    )
    chunk_size: int = Field(
        default=1048576,  # 1MB
        ge=1024,
        le=104857600,  # 100MB
        description="下載區塊大小（位元組）"
    )
    output_directory: str = Field(
        default="./downloads",
        description="預設輸出目錄"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="最大重試次數"
    )
    retry_delay: float = Field(
        default=1.0,
        ge=0.1,
        le=60.0,
        description="重試延遲時間（秒）"
    )
    timeout: int = Field(
        default=300,
        ge=30,
        le=3600,
        description="下載超時時間（秒）"
    )

    if PYDANTIC_V2:
        @field_validator('chunk_size')
        @classmethod
        def validate_chunk_size(cls, v):
            """驗證區塊大小是 256 的倍數"""
            if v % 256 != 0:
                raise ValueError('chunk_size 必須是 256 的倍數')
            return v

        @field_validator('output_directory')
        @classmethod
        def validate_output_directory(cls, v):
            """驗證輸出目錄路徑"""
            if not v or v.strip() == '':
                raise ValueError('output_directory 不能為空')
            return v
    else:
        @validator('chunk_size')
        def validate_chunk_size(cls, v):
            if v % 256 != 0:
                raise ValueError('chunk_size 必須是 256 的倍數')
            return v

        @validator('output_directory')
        def validate_output_directory(cls, v):
            if not v or v.strip() == '':
                raise ValueError('output_directory 不能為空')
            return v


class AuthConfig(BaseModel):
    """認證配置"""

    credentials_file: str = Field(
        default="credentials.json",
        description="OAuth 認證檔案路徑"
    )
    token_file: str = Field(
        default="token.pickle",
        description="令牌儲存檔案路徑"
    )
    scopes: List[str] = Field(
        default=['https://www.googleapis.com/auth/drive.readonly'],
        description="Google API 權限範圍"
    )
    redirect_uri: str = Field(
        default="http://localhost:8080",
        description="OAuth 重定向 URI"
    )
    port: int = Field(
        default=9876,
        ge=1024,
        le=65535,
        description="OAuth 本地伺服器端口"
    )
    prefer_adc: bool = Field(
        default=True,
        description="優先使用 ADC（Application Default Credentials）"
    )

    if PYDANTIC_V2:
        @field_validator('scopes')
        @classmethod
        def validate_scopes(cls, v):
            """驗證 scopes 不為空"""
            if not v:
                raise ValueError('scopes 不能為空')
            return v
    else:
        @validator('scopes')
        def validate_scopes(cls, v):
            if not v:
                raise ValueError('scopes 不能為空')
            return v


class LoggingConfig(BaseModel):
    """日誌配置"""

    level: str = Field(
        default="INFO",
        description="日誌等級"
    )
    file: str = Field(
        default="logs/app.log",
        description="日誌檔案路徑"
    )
    max_size: int = Field(
        default=10485760,  # 10MB
        ge=1024,
        le=104857600,  # 100MB
        description="日誌檔案最大大小（位元組）"
    )
    backup_count: int = Field(
        default=5,
        ge=0,
        le=20,
        description="日誌備份數量"
    )
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="日誌格式"
    )

    if PYDANTIC_V2:
        @field_validator('level')
        @classmethod
        def validate_level(cls, v):
            """驗證日誌等級"""
            valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            if v.upper() not in valid_levels:
                raise ValueError(f'level 必須是以下之一: {valid_levels}')
            return v.upper()
    else:
        @validator('level')
        def validate_level(cls, v):
            valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            if v.upper() not in valid_levels:
                raise ValueError(f'level 必須是以下之一: {valid_levels}')
            return v.upper()


class DatabaseConfig(BaseModel):
    """資料庫配置"""

    url: str = Field(
        default="sqlite:///data/downloads.db",
        description="資料庫連接 URL"
    )
    echo: bool = Field(
        default=False,
        description="是否輸出 SQL 日誌"
    )


class WebConfig(BaseModel):
    """Web 服務配置"""

    host: str = Field(
        default="127.0.0.1",
        description="Web 服務主機"
    )
    port: int = Field(
        default=8000,
        ge=1024,
        le=65535,
        description="Web 服務端口"
    )
    debug: bool = Field(
        default=False,
        description="是否啟用除錯模式"
    )


class UIConfig(BaseModel):
    """UI 配置"""

    progress_update_interval: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="進度更新間隔（秒）"
    )
    theme: str = Field(
        default="light",
        description="UI 主題"
    )
    page_size: int = Field(
        default=50,
        ge=10,
        le=100,
        description="分頁大小"
    )

    if PYDANTIC_V2:
        @field_validator('theme')
        @classmethod
        def validate_theme(cls, v):
            """驗證主題"""
            valid_themes = ['light', 'dark', 'auto']
            if v.lower() not in valid_themes:
                raise ValueError(f'theme 必須是以下之一: {valid_themes}')
            return v.lower()
    else:
        @validator('theme')
        def validate_theme(cls, v):
            valid_themes = ['light', 'dark', 'auto']
            if v.lower() not in valid_themes:
                raise ValueError(f'theme 必須是以下之一: {valid_themes}')
            return v.lower()


class RetryConfig(BaseModel):
    """重試配置"""

    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="最大重試次數"
    )
    base_delay: float = Field(
        default=1.0,
        ge=0.1,
        le=30.0,
        description="基礎延遲時間（秒）"
    )
    max_delay: float = Field(
        default=60.0,
        ge=1.0,
        le=300.0,
        description="最大延遲時間（秒）"
    )
    backoff_factor: float = Field(
        default=2.0,
        ge=1.0,
        le=5.0,
        description="退避因子"
    )
    jitter: bool = Field(
        default=True,
        description="是否添加隨機抖動"
    )


class AppConfig(BaseModel):
    """應用程式主配置"""

    download: DownloadConfig = Field(default_factory=DownloadConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    web: WebConfig = Field(default_factory=WebConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)

    class Config:
        """Pydantic 配置"""
        validate_assignment = True
        extra = 'allow'  # 允許額外欄位

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppConfig':
        """從字典建立配置

        Args:
            data: 配置字典

        Returns:
            AppConfig 實例
        """
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典

        Returns:
            配置字典
        """
        if PYDANTIC_V2:
            return self.model_dump()
        else:
            return self.dict()

    def get(self, key: str, default: Any = None) -> Any:
        """取得配置值（支援點號分隔）

        Args:
            key: 配置鍵，例如 'download.max_concurrent'
            default: 預設值

        Returns:
            配置值
        """
        keys = key.split('.')
        value = self

        for k in keys:
            if hasattr(value, k):
                value = getattr(value, k)
            elif isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """設定配置值（支援點號分隔）

        Args:
            key: 配置鍵
            value: 配置值
        """
        keys = key.split('.')

        if len(keys) == 1:
            setattr(self, key, value)
        else:
            section = getattr(self, keys[0], None)
            if section and hasattr(section, keys[1]):
                setattr(section, keys[1], value)


def create_default_config() -> AppConfig:
    """建立預設配置

    Returns:
        AppConfig 實例
    """
    return AppConfig()


def load_config_from_yaml(file_path: str) -> AppConfig:
    """從 YAML 檔案載入配置

    Args:
        file_path: YAML 檔案路徑

    Returns:
        AppConfig 實例

    Raises:
        FileNotFoundError: 檔案不存在
        ValueError: 配置格式錯誤
    """
    import yaml

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"配置檔案不存在: {file_path}")

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}

        return AppConfig.from_dict(data)

    except yaml.YAMLError as e:
        raise ValueError(f"YAML 格式錯誤: {e}")


def save_config_to_yaml(config: AppConfig, file_path: str):
    """儲存配置到 YAML 檔案

    Args:
        config: AppConfig 實例
        file_path: YAML 檔案路徑
    """
    import yaml

    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(
            config.to_dict(),
            f,
            default_flow_style=False,
            allow_unicode=True,
            indent=2
        )


def validate_config(config: AppConfig) -> tuple[bool, List[str]]:
    """驗證配置

    Args:
        config: AppConfig 實例

    Returns:
        (是否有效, 錯誤訊息列表)
    """
    errors = []

    # 驗證下載配置
    if config.download.max_concurrent > 10:
        errors.append("建議 max_concurrent 不要超過 10，以避免被 Google 限制")

    if config.download.chunk_size > 10485760:  # 10MB
        errors.append("建議 chunk_size 不要超過 10MB")

    # 驗證認證配置
    if not config.auth.scopes:
        errors.append("auth.scopes 不能為空")

    # 驗證日誌配置
    try:
        Path(config.logging.file).parent
    except Exception:
        errors.append("logging.file 路徑無效")

    return len(errors) == 0, errors
