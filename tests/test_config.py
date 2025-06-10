"""
配置管理器測試
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch

from src.utils.config import ConfigManager


class TestConfigManager:
    """配置管理器測試類別"""
    
    def test_init_with_existing_config(self):
        """測試使用現有配置檔案初始化"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            test_config = {
                'download': {'max_concurrent': 10},
                'auth': {'scopes': ['test-scope']}
            }
            yaml.dump(test_config, f)
            config_path = f.name
        
        try:
            manager = ConfigManager(config_path)
            assert manager.get('download.max_concurrent') == 10
            assert manager.get('auth.scopes') == ['test-scope']
        finally:
            Path(config_path).unlink()
    
    def test_init_without_config_creates_default(self):
        """測試沒有配置檔案時建立預設配置"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / 'test_config.yaml'
            manager = ConfigManager(str(config_path))
            
            # 檢查預設配置
            assert manager.get('download.max_concurrent') == 5
            assert manager.get('auth.scopes') == ['https://www.googleapis.com/auth/drive.readonly']
            assert config_path.exists()
    
    def test_get_with_dot_notation(self):
        """測試點號分隔的配置取得"""
        manager = ConfigManager()
        
        # 測試存在的配置
        assert isinstance(manager.get('download.max_concurrent'), int)
        
        # 測試不存在的配置
        assert manager.get('nonexistent.key') is None
        assert manager.get('nonexistent.key', 'default') == 'default'
    
    def test_set_configuration(self):
        """測試設定配置值"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / 'test_config.yaml'
            manager = ConfigManager(str(config_path))
            
            # 設定新值
            manager.set('download.max_concurrent', 20)
            assert manager.get('download.max_concurrent') == 20
            
            # 設定嵌套值
            manager.set('new.nested.value', 'test')
            assert manager.get('new.nested.value') == 'test'
    
    def test_get_section(self):
        """測試取得整個配置區段"""
        manager = ConfigManager()
        
        download_config = manager.get_section('download')
        assert isinstance(download_config, dict)
        assert 'max_concurrent' in download_config
        assert 'chunk_size' in download_config
    
    def test_save_and_reload(self):
        """測試配置儲存和重新載入"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / 'test_config.yaml'
            manager = ConfigManager(str(config_path))
            
            # 修改配置
            manager.set('test.value', 42)
            manager.save_config()
            
            # 重新載入
            manager.reload()
            assert manager.get('test.value') == 42
    
    def test_validate_config(self):
        """測試配置驗證"""
        manager = ConfigManager()
        
        # 正常配置應該通過驗證
        assert manager.validate_config() is True
        
        # 設定無效的配置
        manager.set('download.max_concurrent', 'invalid')
        assert manager.validate_config() is False
        
        # 恢復有效配置
        manager.set('download.max_concurrent', 5)
        assert manager.validate_config() is True
    
    def test_update_from_dict(self):
        """測試從字典更新配置"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / 'test_config.yaml'
            manager = ConfigManager(str(config_path))
            
            # 更新配置
            updates = {
                'download': {
                    'max_concurrent': 15,
                    'new_setting': 'test'
                },
                'new_section': {
                    'value': 123
                }
            }
            
            manager.update_from_dict(updates)
            
            # 驗證更新
            assert manager.get('download.max_concurrent') == 15
            assert manager.get('download.new_setting') == 'test'
            assert manager.get('new_section.value') == 123
            
            # 確保原有配置仍然存在
            assert manager.get('download.chunk_size') is not None


@pytest.fixture
def temp_config():
    """臨時配置檔案 fixture"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        test_config = {
            'download': {
                'max_concurrent': 3,
                'chunk_size': 512000,
                'output_directory': './test_downloads'
            },
            'auth': {
                'scopes': ['https://www.googleapis.com/auth/drive.readonly']
            }
        }
        yaml.dump(test_config, f)
        config_path = f.name
    
    yield config_path
    
    # 清理
    Path(config_path).unlink()


def test_config_with_fixture(temp_config):
    """使用 fixture 測試配置載入"""
    manager = ConfigManager(temp_config)
    
    assert manager.get('download.max_concurrent') == 3
    assert manager.get('download.chunk_size') == 512000
    assert manager.get('download.output_directory') == './test_downloads' 