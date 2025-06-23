"""
安全令牌儲存系統
提供加密的令牌儲存和管理功能
"""

import os
import pickle
import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    import base64
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False

from ..utils.logger import LoggerMixin
from ..utils.exceptions import AuthenticationError


class SecureTokenStorage(LoggerMixin):
    """安全令牌儲存器
    
    提供加密的令牌儲存、有效期管理和安全清理功能
    """
    
    def __init__(self, 
                 storage_dir: str = "tokens",
                 encryption_key_file: str = None,
                 enable_encryption: bool = True,
                 token_ttl_hours: int = 24):
        """
        初始化安全令牌儲存器
        
        Args:
            storage_dir: 令牌儲存目錄
            encryption_key_file: 加密金鑰檔案路徑
            enable_encryption: 是否啟用加密
            token_ttl_hours: 令牌有效期（小時）
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.encryption_key_file = encryption_key_file or str(self.storage_dir / "encryption.key")
        self.enable_encryption = enable_encryption and ENCRYPTION_AVAILABLE
        self.token_ttl = timedelta(hours=token_ttl_hours)
        
        # 初始化加密
        self._fernet = None
        if self.enable_encryption:
            self._init_encryption()
        else:
            if enable_encryption:
                self.logger.warning("cryptography 套件未安裝，無法使用加密功能")
        
        # 元資料檔案
        self.metadata_file = self.storage_dir / "tokens_metadata.json"
        self._metadata = self._load_metadata()
        
        self.logger.info(f"安全令牌儲存器已初始化 - 加密: {self.enable_encryption}")
    
    def _init_encryption(self):
        """初始化加密系統"""
        try:
            if not os.path.exists(self.encryption_key_file):
                # 生成新的加密金鑰
                key = Fernet.generate_key()
                self._save_key(key)
                self.logger.info("已生成新的加密金鑰")
            else:
                # 載入現有金鑰
                key = self._load_key()
                self.logger.info("已載入現有加密金鑰")
            
            self._fernet = Fernet(key)
            
        except Exception as e:
            self.logger.error(f"初始化加密系統失敗: {e}")
            self.enable_encryption = False
    
    def _save_key(self, key: bytes):
        """儲存加密金鑰"""
        key_path = Path(self.encryption_key_file)
        key_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(key_path, 'wb') as f:
            f.write(key)
        
        # 設定檔案權限（僅擁有者可讀寫）
        try:
            os.chmod(key_path, 0o600)
        except (OSError, AttributeError):
            # Windows 或其他不支援 chmod 的系統
            pass
    
    def _load_key(self) -> bytes:
        """載入加密金鑰"""
        with open(self.encryption_key_file, 'rb') as f:
            return f.read()
    
    def _load_metadata(self) -> Dict[str, Any]:
        """載入令牌元資料"""
        if not self.metadata_file.exists():
            return {}
        
        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.warning(f"載入元資料失敗: {e}")
            return {}
    
    def _save_metadata(self):
        """儲存令牌元資料"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self._metadata, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            self.logger.error(f"儲存元資料失敗: {e}")
    
    def _encrypt_data(self, data: bytes) -> bytes:
        """加密資料"""
        if self.enable_encryption and self._fernet:
            return self._fernet.encrypt(data)
        else:
            return data
    
    def _decrypt_data(self, encrypted_data: bytes) -> bytes:
        """解密資料"""
        if self.enable_encryption and self._fernet:
            try:
                return self._fernet.decrypt(encrypted_data)
            except Exception as e:
                self.logger.error(f"解密失敗: {e}")
                raise AuthenticationError("令牌解密失敗，可能已損毀")
        else:
            return encrypted_data
    
    def _generate_token_id(self, auth_type: str, identifier: str = None) -> str:
        """生成令牌 ID"""
        # 使用認證類型和識別符生成唯一 ID
        content = f"{auth_type}_{identifier or 'default'}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def save_token(self, 
                   token_data: Any, 
                   auth_type: str, 
                   identifier: str = None,
                   user_info: Dict[str, Any] = None) -> str:
        """儲存令牌
        
        Args:
            token_data: 令牌資料（Credentials 物件或其他）
            auth_type: 認證類型
            identifier: 識別符（如使用者 email）
            user_info: 使用者資訊
            
        Returns:
            令牌 ID
        """
        try:
            token_id = self._generate_token_id(auth_type, identifier)
            token_file = self.storage_dir / f"{token_id}.token"
            
            # 序列化令牌資料
            serialized_data = pickle.dumps(token_data)
            
            # 加密並儲存
            encrypted_data = self._encrypt_data(serialized_data)
            
            with open(token_file, 'wb') as f:
                f.write(encrypted_data)
            
            # 設定檔案權限
            try:
                os.chmod(token_file, 0o600)
            except (OSError, AttributeError):
                pass
            
            # 更新元資料
            self._metadata[token_id] = {
                'auth_type': auth_type,
                'identifier': identifier,
                'user_info': user_info or {},
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + self.token_ttl).isoformat(),
                'file_path': str(token_file),
                'encrypted': self.enable_encryption
            }
            
            self._save_metadata()
            
            self.logger.info(f"令牌已儲存 - ID: {token_id}, 類型: {auth_type}")
            return token_id
            
        except Exception as e:
            self.logger.error(f"儲存令牌失敗: {e}")
            raise AuthenticationError(f"無法儲存令牌: {e}")
    
    def load_token(self, token_id: str = None, auth_type: str = None, identifier: str = None) -> Optional[Any]:
        """載入令牌
        
        Args:
            token_id: 令牌 ID
            auth_type: 認證類型（用於自動查找）
            identifier: 識別符（用於自動查找）
            
        Returns:
            令牌資料，如果不存在或已過期則返回 None
        """
        try:
            # 如果沒有提供 token_id，嘗試生成
            if not token_id and auth_type:
                token_id = self._generate_token_id(auth_type, identifier)
            
            if not token_id or token_id not in self._metadata:
                self.logger.debug(f"令牌不存在: {token_id}")
                return None
            
            metadata = self._metadata[token_id]
            
            # 檢查是否已過期
            expires_at = datetime.fromisoformat(metadata['expires_at'])
            if datetime.now() > expires_at:
                self.logger.info(f"令牌已過期: {token_id}")
                self.delete_token(token_id)
                return None
            
            # 載入令牌檔案
            token_file = Path(metadata['file_path'])
            if not token_file.exists():
                self.logger.warning(f"令牌檔案不存在: {token_file}")
                del self._metadata[token_id]
                self._save_metadata()
                return None
            
            with open(token_file, 'rb') as f:
                encrypted_data = f.read()
            
            # 解密和反序列化
            decrypted_data = self._decrypt_data(encrypted_data)
            token_data = pickle.loads(decrypted_data)
            
            self.logger.debug(f"令牌已載入: {token_id}")
            return token_data
            
        except Exception as e:
            self.logger.error(f"載入令牌失敗: {e}")
            return None
    
    def delete_token(self, token_id: str):
        """刪除令牌
        
        Args:
            token_id: 令牌 ID
        """
        try:
            if token_id in self._metadata:
                metadata = self._metadata[token_id]
                token_file = Path(metadata['file_path'])
                
                # 刪除檔案
                if token_file.exists():
                    token_file.unlink()
                    self.logger.info(f"令牌檔案已刪除: {token_file}")
                
                # 從元資料中移除
                del self._metadata[token_id]
                self._save_metadata()
                
                self.logger.info(f"令牌已刪除: {token_id}")
        
        except Exception as e:
            self.logger.error(f"刪除令牌失敗: {e}")
    
    def list_tokens(self) -> Dict[str, Dict[str, Any]]:
        """列出所有令牌
        
        Returns:
            令牌清單字典
        """
        return self._metadata.copy()
    
    def cleanup_expired_tokens(self) -> int:
        """清理過期的令牌
        
        Returns:
            清理的令牌數量
        """
        now = datetime.now()
        expired_tokens = []
        
        for token_id, metadata in self._metadata.items():
            expires_at = datetime.fromisoformat(metadata['expires_at'])
            if now > expires_at:
                expired_tokens.append(token_id)
        
        for token_id in expired_tokens:
            self.delete_token(token_id)
        
        if expired_tokens:
            self.logger.info(f"已清理 {len(expired_tokens)} 個過期令牌")
        
        return len(expired_tokens)
    
    def get_token_info(self, token_id: str) -> Optional[Dict[str, Any]]:
        """取得令牌資訊
        
        Args:
            token_id: 令牌 ID
            
        Returns:
            令牌資訊字典
        """
        if token_id in self._metadata:
            metadata = self._metadata[token_id].copy()
            
            # 檢查是否過期
            expires_at = datetime.fromisoformat(metadata['expires_at'])
            metadata['is_expired'] = datetime.now() > expires_at
            metadata['is_valid'] = not metadata['is_expired']
            
            return metadata
        
        return None
    
    def change_encryption_key(self, new_key_file: str = None):
        """更換加密金鑰
        
        Args:
            new_key_file: 新的金鑰檔案路徑
        """
        if not self.enable_encryption:
            self.logger.warning("加密功能未啟用，無法更換金鑰")
            return
        
        try:
            # 載入所有現有令牌
            tokens_data = {}
            for token_id in list(self._metadata.keys()):
                token_data = self.load_token(token_id)
                if token_data:
                    tokens_data[token_id] = (token_data, self._metadata[token_id])
            
            # 生成新金鑰
            new_key = Fernet.generate_key()
            old_key_file = self.encryption_key_file
            
            if new_key_file:
                self.encryption_key_file = new_key_file
            
            # 儲存新金鑰
            self._save_key(new_key)
            self._fernet = Fernet(new_key)
            
            # 重新加密所有令牌
            for token_id, (token_data, metadata) in tokens_data.items():
                self.delete_token(token_id)
                self.save_token(
                    token_data,
                    metadata['auth_type'],
                    metadata['identifier'],
                    metadata['user_info']
                )
            
            # 刪除舊金鑰檔案
            if old_key_file != self.encryption_key_file:
                try:
                    os.unlink(old_key_file)
                except:
                    pass
            
            self.logger.info("加密金鑰已更換，所有令牌已重新加密")
            
        except Exception as e:
            self.logger.error(f"更換加密金鑰失敗: {e}")
            raise AuthenticationError(f"無法更換加密金鑰: {e}")


# 全域安全令牌儲存實例
secure_token_storage = SecureTokenStorage()


def get_secure_token(auth_type: str, identifier: str = None) -> Optional[Any]:
    """便利函數：取得安全令牌
    
    Args:
        auth_type: 認證類型
        identifier: 識別符
        
    Returns:
        令牌資料
    """
    return secure_token_storage.load_token(auth_type=auth_type, identifier=identifier)


def save_secure_token(token_data: Any, auth_type: str, identifier: str = None, user_info: Dict[str, Any] = None) -> str:
    """便利函數：儲存安全令牌
    
    Args:
        token_data: 令牌資料
        auth_type: 認證類型
        identifier: 識別符
        user_info: 使用者資訊
        
    Returns:
        令牌 ID
    """
    return secure_token_storage.save_token(token_data, auth_type, identifier, user_info) 