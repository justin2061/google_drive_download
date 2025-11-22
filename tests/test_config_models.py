"""
Pydantic 配置模型測試
"""

import pytest
import tempfile
from pathlib import Path
import sys
import yaml

sys.path.append(str(Path(__file__).parent.parent))

from src.utils.config_models import (
    DownloadConfig,
    AuthConfig,
    LoggingConfig,
    DatabaseConfig,
    WebConfig,
    UIConfig,
    RetryConfig,
    AppConfig,
    create_default_config,
    load_config_from_yaml,
    save_config_to_yaml,
    validate_config
)


class TestDownloadConfig:
    """測試下載配置"""

    def test_default_values(self):
        """測試預設值"""
        config = DownloadConfig()

        assert config.max_concurrent == 5
        assert config.chunk_size == 1048576
        assert config.output_directory == "./downloads"
        assert config.max_retries == 3
        assert config.timeout == 300

    def test_custom_values(self):
        """測試自訂值"""
        config = DownloadConfig(
            max_concurrent=10,
            chunk_size=2097152,
            output_directory="./custom"
        )

        assert config.max_concurrent == 10
        assert config.chunk_size == 2097152
        assert config.output_directory == "./custom"

    def test_max_concurrent_range(self):
        """測試 max_concurrent 範圍驗證"""
        with pytest.raises(ValueError):
            DownloadConfig(max_concurrent=0)

        with pytest.raises(ValueError):
            DownloadConfig(max_concurrent=25)

    def test_chunk_size_validation(self):
        """測試 chunk_size 驗證"""
        # 必須是 256 的倍數
        with pytest.raises(ValueError):
            DownloadConfig(chunk_size=1000)  # 不是 256 的倍數

        # 有效的 chunk_size
        config = DownloadConfig(chunk_size=1024)
        assert config.chunk_size == 1024

    def test_timeout_range(self):
        """測試 timeout 範圍驗證"""
        with pytest.raises(ValueError):
            DownloadConfig(timeout=10)  # 小於最小值 30

        with pytest.raises(ValueError):
            DownloadConfig(timeout=7200)  # 大於最大值 3600


class TestAuthConfig:
    """測試認證配置"""

    def test_default_values(self):
        """測試預設值"""
        config = AuthConfig()

        assert config.credentials_file == "credentials.json"
        assert config.token_file == "token.pickle"
        assert len(config.scopes) > 0
        assert config.port == 9876
        assert config.prefer_adc is True

    def test_custom_scopes(self):
        """測試自訂 scopes"""
        config = AuthConfig(
            scopes=['https://www.googleapis.com/auth/drive']
        )

        assert len(config.scopes) == 1
        assert 'drive' in config.scopes[0]

    def test_empty_scopes_validation(self):
        """測試空 scopes 驗證"""
        with pytest.raises(ValueError):
            AuthConfig(scopes=[])

    def test_port_range(self):
        """測試端口範圍驗證"""
        with pytest.raises(ValueError):
            AuthConfig(port=80)  # 小於最小值 1024

        with pytest.raises(ValueError):
            AuthConfig(port=70000)  # 大於最大值 65535


class TestLoggingConfig:
    """測試日誌配置"""

    def test_default_values(self):
        """測試預設值"""
        config = LoggingConfig()

        assert config.level == "INFO"
        assert config.file == "logs/app.log"
        assert config.backup_count == 5

    def test_level_validation(self):
        """測試日誌等級驗證"""
        # 有效等級
        config = LoggingConfig(level="DEBUG")
        assert config.level == "DEBUG"

        # 應該轉換為大寫
        config = LoggingConfig(level="warning")
        assert config.level == "WARNING"

        # 無效等級
        with pytest.raises(ValueError):
            LoggingConfig(level="INVALID")


class TestUIConfig:
    """測試 UI 配置"""

    def test_default_values(self):
        """測試預設值"""
        config = UIConfig()

        assert config.progress_update_interval == 1.0
        assert config.theme == "light"
        assert config.page_size == 50

    def test_theme_validation(self):
        """測試主題驗證"""
        config = UIConfig(theme="dark")
        assert config.theme == "dark"

        # 應該轉換為小寫
        config = UIConfig(theme="LIGHT")
        assert config.theme == "light"

        # 無效主題
        with pytest.raises(ValueError):
            UIConfig(theme="invalid")

    def test_page_size_range(self):
        """測試分頁大小範圍"""
        with pytest.raises(ValueError):
            UIConfig(page_size=5)  # 小於最小值 10

        with pytest.raises(ValueError):
            UIConfig(page_size=200)  # 大於最大值 100


class TestRetryConfig:
    """測試重試配置"""

    def test_default_values(self):
        """測試預設值"""
        config = RetryConfig()

        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.backoff_factor == 2.0
        assert config.jitter is True

    def test_backoff_factor_range(self):
        """測試退避因子範圍"""
        with pytest.raises(ValueError):
            RetryConfig(backoff_factor=0.5)  # 小於最小值 1.0

        with pytest.raises(ValueError):
            RetryConfig(backoff_factor=10.0)  # 大於最大值 5.0


class TestAppConfig:
    """測試應用程式主配置"""

    def test_default_values(self):
        """測試預設值"""
        config = AppConfig()

        assert config.download is not None
        assert config.auth is not None
        assert config.logging is not None
        assert config.database is not None
        assert config.web is not None
        assert config.ui is not None

    def test_from_dict(self):
        """測試從字典建立"""
        data = {
            'download': {
                'max_concurrent': 10
            },
            'auth': {
                'port': 8888
            }
        }

        config = AppConfig.from_dict(data)

        assert config.download.max_concurrent == 10
        assert config.auth.port == 8888

    def test_to_dict(self):
        """測試轉換為字典"""
        config = AppConfig()
        data = config.to_dict()

        assert isinstance(data, dict)
        assert 'download' in data
        assert 'auth' in data
        assert data['download']['max_concurrent'] == 5

    def test_get_with_dot_notation(self):
        """測試點號分隔取值"""
        config = AppConfig()

        assert config.get('download.max_concurrent') == 5
        assert config.get('auth.port') == 9876
        assert config.get('nonexistent.key', 'default') == 'default'

    def test_set_with_dot_notation(self):
        """測試點號分隔設值"""
        config = AppConfig()

        config.set('download.max_concurrent', 8)
        assert config.download.max_concurrent == 8

    def test_nested_defaults(self):
        """測試嵌套預設值"""
        config = AppConfig()

        # 所有嵌套配置都應該有預設值
        assert config.download.chunk_size > 0
        assert len(config.auth.scopes) > 0
        assert config.logging.level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']


class TestCreateDefaultConfig:
    """測試建立預設配置函數"""

    def test_create_default(self):
        """測試建立預設配置"""
        config = create_default_config()

        assert isinstance(config, AppConfig)
        assert config.download.max_concurrent == 5


class TestLoadSaveConfig:
    """測試配置載入和儲存"""

    def test_save_and_load(self):
        """測試儲存和載入"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.yaml"

            # 建立並儲存配置
            config = AppConfig()
            config.download.max_concurrent = 10
            save_config_to_yaml(config, str(config_path))

            # 載入配置
            loaded = load_config_from_yaml(str(config_path))

            assert loaded.download.max_concurrent == 10

    def test_load_nonexistent_file(self):
        """測試載入不存在的檔案"""
        with pytest.raises(FileNotFoundError):
            load_config_from_yaml("/nonexistent/path/config.yaml")

    def test_save_creates_directory(self):
        """測試儲存時建立目錄"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "nested" / "dir" / "config.yaml"

            config = AppConfig()
            save_config_to_yaml(config, str(config_path))

            assert config_path.exists()

    def test_load_invalid_yaml(self):
        """測試載入無效的 YAML"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content:")
            config_path = f.name

        try:
            with pytest.raises(ValueError):
                load_config_from_yaml(config_path)
        finally:
            Path(config_path).unlink()


class TestValidateConfig:
    """測試配置驗證"""

    def test_valid_config(self):
        """測試有效配置"""
        config = AppConfig()
        is_valid, errors = validate_config(config)

        assert is_valid is True
        assert len(errors) == 0

    def test_warning_high_concurrent(self):
        """測試高並發數警告"""
        config = AppConfig()
        config.download.max_concurrent = 15

        is_valid, errors = validate_config(config)

        # 應該有警告但仍然有效
        assert any("max_concurrent" in e for e in errors)

    def test_warning_large_chunk_size(self):
        """測試大區塊大小警告"""
        config = AppConfig()
        config.download.chunk_size = 20971520  # 20MB

        is_valid, errors = validate_config(config)

        assert any("chunk_size" in e for e in errors)


class TestConfigIntegration:
    """配置整合測試"""

    def test_full_workflow(self):
        """測試完整工作流程"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "app_config.yaml"

            # 1. 建立配置
            config = create_default_config()

            # 2. 修改配置
            config.download.max_concurrent = 8
            config.auth.port = 9999
            config.ui.theme = "dark"

            # 3. 儲存配置
            save_config_to_yaml(config, str(config_path))

            # 4. 載入配置
            loaded = load_config_from_yaml(str(config_path))

            # 5. 驗證
            assert loaded.download.max_concurrent == 8
            assert loaded.auth.port == 9999
            assert loaded.ui.theme == "dark"

            # 6. 驗證配置有效性
            is_valid, errors = validate_config(loaded)
            assert is_valid is True


if __name__ == '__main__':
    pytest.main([__file__])
