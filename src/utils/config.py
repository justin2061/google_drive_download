"""
配置管理模組
提供系統配置的載入、儲存和管理功能
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器
    
    負責載入、儲存和管理系統配置
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self):
        """載入配置檔案"""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"配置檔案不存在: {self.config_path}\n"
                f"請確保專案根目錄下有 config.yaml 檔案。\n"
                f"您可以參考 config.yaml.backup 作為範本。"
            )
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                self._config = yaml.safe_load(file) or {}
            logger.info(f"配置檔案已載入: {self.config_path}")
            
            if not self._config:
                raise ValueError(f"配置檔案為空或格式錯誤: {self.config_path}")
                
        except yaml.YAMLError as e:
            raise ValueError(f"配置檔案 YAML 格式錯誤: {self.config_path}\n錯誤詳情: {e}")
        except Exception as e:
            raise RuntimeError(f"載入配置檔案時發生未預期的錯誤: {e}")
    
    def _create_default_config(self):
        """建立預設配置檔案"""
        default_config = {
            'download': {
                'max_concurrent': 5,
                'chunk_size': 1048576,  # 1MB
                'output_directory': './downloads',
                'max_retries': 3,
                'retry_delay': 1.0,
                'timeout': 300  # 5 minutes
            },
            'auth': {
                'credentials_file': 'credentials.json',
                'token_file': 'token.pickle',
                'scopes': [
                    'https://www.googleapis.com/auth/drive.readonly'
                ],
                'redirect_uri': 'http://localhost:8080'
            },
            'logging': {
                'level': 'INFO',
                'file': 'logs/app.log',
                'max_size': 10485760,  # 10MB
                'backup_count': 5,
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
            'database': {
                'url': 'sqlite:///data/downloads.db',
                'echo': False
            },
            'web': {
                'host': '127.0.0.1',
                'port': 8000,
                'debug': False
            },
            'ui': {
                'progress_update_interval': 1.0,  # seconds
                'theme': 'light'
            }
        }
        
        self._config = default_config
        self.save_config()
    
    def get(self, key: str, default: Any = None) -> Any:
        """取得配置值
        
        Args:
            key: 配置鍵，支援點號分隔的階層式存取 (e.g., 'download.max_concurrent')
            default: 預設值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """設定配置值
        
        Args:
            key: 配置鍵，支援點號分隔的階層式存取
            value: 配置值
        """
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        logger.info(f"配置已更新: {key} = {value}")
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """取得整個配置區段
        
        Args:
            section: 區段名稱
            
        Returns:
            配置區段字典
        """
        return self.get(section, {})
    
    def save_config(self):
        """儲存配置到檔案"""
        try:
            # 確保目錄存在
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as file:
                yaml.dump(
                    self._config, 
                    file, 
                    default_flow_style=False, 
                    allow_unicode=True,
                    indent=2
                )
            logger.info(f"配置已儲存: {self.config_path}")
        except Exception as e:
            logger.error(f"儲存配置檔案失敗: {e}")
            raise
    
    def reload(self):
        """重新載入配置"""
        logger.info("重新載入配置檔案")
        self._load_config()
    
    def validate_config(self) -> bool:
        """驗證配置的有效性
        
        Returns:
            True if valid, False otherwise
        """
        required_sections = ['download', 'auth', 'logging']
        
        for section in required_sections:
            if section not in self._config:
                logger.error(f"缺少必要的配置區段: {section}")
                return False
        
        # 驗證數值範圍
        max_concurrent = self.get('download.max_concurrent', 0)
        if not isinstance(max_concurrent, int) or max_concurrent <= 0:
            logger.error("download.max_concurrent 必須是正整數")
            return False
        
        chunk_size = self.get('download.chunk_size', 0)
        if not isinstance(chunk_size, int) or chunk_size <= 0:
            logger.error("download.chunk_size 必須是正整數")
            return False
        
        return True
    
    def get_all(self) -> Dict[str, Any]:
        """取得所有配置
        
        Returns:
            完整的配置字典
        """
        return self._config.copy()
    
    def update_from_dict(self, updates: Dict[str, Any]):
        """從字典更新配置
        
        Args:
            updates: 要更新的配置字典
        """
        def deep_update(base_dict, update_dict):
            for key, value in update_dict.items():
                if isinstance(value, dict) and key in base_dict:
                    deep_update(base_dict[key], value)
                else:
                    base_dict[key] = value
        
        deep_update(self._config, updates)
        logger.info("配置已從字典更新")


# 全域配置實例
config = ConfigManager()

# 便利函數
def get_config(key: str, default: Any = None) -> Any:
    """全域配置取得函數"""
    value = config.get(key, default)
    if value is None and default is None:
        raise ValueError(
            f"配置項 '{key}' 不存在且未提供預設值。\n"
            f"請檢查 config.yaml 檔案中是否正確設定了此配置項。"
        )
    return value

def set_config(key: str, value: Any):
    """全域配置設定函數"""
    config.set(key, value)

def save_config():
    """全域配置儲存函數"""
    config.save_config()

def load_config(config_path: str = None) -> Dict[str, Any]:
    """載入配置檔案
    
    Args:
        config_path: 配置檔案路徑，如果為 None 則使用預設路徑
        
    Returns:
        配置字典
    """
    if config_path:
        temp_config = ConfigManager(config_path)
        return temp_config.get_all()
    else:
        return config.get_all() 