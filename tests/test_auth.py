"""
認證模組測試
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.core.auth import GoogleOAuthProvider, AuthManager
from src.utils.exceptions import AuthenticationError, ConfigurationError


class TestGoogleOAuthProvider:
    """測試 Google OAuth 提供者"""
    
    def setup_method(self):
        """測試前設定"""
        self.temp_dir = tempfile.mkdtemp()
        self.credentials_file = os.path.join(self.temp_dir, 'credentials.json')
        self.token_file = os.path.join(self.temp_dir, 'token.pickle')
        
        # 建立假的認證檔案
        with open(self.credentials_file, 'w') as f:
            f.write('{"type": "service_account"}')
        
        self.provider = GoogleOAuthProvider(
            credentials_file=self.credentials_file,
            token_file=self.token_file
        )
    
    def test_init(self):
        """測試初始化"""
        assert self.provider.credentials_file == self.credentials_file
        assert self.provider.token_file == self.token_file
        assert len(self.provider.scopes) > 0
    
    @patch('src.core.auth.pickle.load')
    def test_load_token_success(self, mock_load):
        """測試載入令牌成功"""
        mock_credentials = Mock()
        mock_load.return_value = mock_credentials
        
        # 建立令牌檔案
        Path(self.token_file).touch()
        
        result = self.provider._load_token()
        
        assert result == mock_credentials
        mock_load.assert_called_once()
    
    def test_load_token_file_not_exists(self):
        """測試令牌檔案不存在"""
        result = self.provider._load_token()
        assert result is None
    
    @patch('src.core.auth.pickle.dump')
    def test_save_token_success(self, mock_dump):
        """測試儲存令牌成功"""
        mock_credentials = Mock()
        
        self.provider._save_token(mock_credentials)
        
        mock_dump.assert_called_once_with(mock_credentials, unittest.mock.ANY)
        assert Path(self.token_file).exists()
    
    def test_run_oauth_flow_no_credentials(self):
        """測試 OAuth 流程 - 沒有認證檔案"""
        os.remove(self.credentials_file)
        
        with pytest.raises(ConfigurationError):
            self.provider._run_oauth_flow()
    
    @patch('src.core.auth.InstalledAppFlow.from_client_secrets_file')
    def test_run_oauth_flow_success(self, mock_flow_class):
        """測試 OAuth 流程成功"""
        mock_flow = Mock()
        mock_credentials = Mock()
        mock_flow.run_local_server.return_value = mock_credentials
        mock_flow_class.return_value = mock_flow
        
        result = self.provider._run_oauth_flow()
        
        assert result == mock_credentials
        mock_flow_class.assert_called_once()
        mock_flow.run_local_server.assert_called_once()
    
    def test_is_authenticated_false(self):
        """測試未認證狀態"""
        assert not self.provider.is_authenticated()
    
    @patch('src.core.auth.GoogleOAuthProvider._load_token')
    def test_authenticate_existing_valid_token(self, mock_load_token):
        """測試使用現有有效令牌認證"""
        mock_credentials = Mock()
        mock_credentials.valid = True
        mock_load_token.return_value = mock_credentials
        
        result = self.provider.authenticate()
        
        assert result is True
        assert self.provider._credentials == mock_credentials


class TestAuthManager:
    """測試認證管理器"""
    
    def setup_method(self):
        """測試前設定"""
        self.mock_oauth_provider = Mock(spec=GoogleOAuthProvider)
        self.auth_manager = AuthManager(oauth_provider=self.mock_oauth_provider)
    
    def test_init(self):
        """測試初始化"""
        assert self.auth_manager.oauth_provider == self.mock_oauth_provider
        assert self.auth_manager._drive_service is None
        assert len(self.auth_manager._service_cache) == 0
    
    def test_authenticate_success(self):
        """測試認證成功"""
        self.mock_oauth_provider.authenticate.return_value = True
        
        result = self.auth_manager.authenticate()
        
        assert result is True
        self.mock_oauth_provider.authenticate.assert_called_once_with(False)
    
    def test_authenticate_failure(self):
        """測試認證失敗"""
        self.mock_oauth_provider.authenticate.return_value = False
        
        result = self.auth_manager.authenticate()
        
        assert result is False
    
    @patch('src.core.auth.build')
    def test_get_drive_service_success(self, mock_build):
        """測試取得 Drive 服務成功"""
        mock_credentials = Mock()
        mock_service = Mock()
        
        self.mock_oauth_provider.get_credentials.return_value = mock_credentials
        mock_build.return_value = mock_service
        
        result = self.auth_manager.get_drive_service()
        
        assert result == mock_service
        mock_build.assert_called_once_with(
            'drive', 'v3', 
            credentials=mock_credentials, 
            cache_discovery=False
        )
    
    def test_get_drive_service_no_credentials(self):
        """測試取得 Drive 服務 - 沒有認證"""
        self.mock_oauth_provider.get_credentials.return_value = None
        
        with pytest.raises(AuthenticationError):
            self.auth_manager.get_drive_service()
    
    def test_is_authenticated(self):
        """測試認證狀態檢查"""
        self.mock_oauth_provider.is_authenticated.return_value = True
        
        result = self.auth_manager.is_authenticated()
        
        assert result is True
        self.mock_oauth_provider.is_authenticated.assert_called_once()
    
    @patch('src.core.auth.build')
    def test_test_connection_success(self, mock_build):
        """測試連線成功"""
        mock_service = Mock()
        mock_about = Mock()
        mock_about.get.return_value.execute.return_value = {
            'user': {'emailAddress': 'test@example.com'}
        }
        mock_service.about.return_value = mock_about
        
        self.mock_oauth_provider.get_credentials.return_value = Mock()
        mock_build.return_value = mock_service
        
        result = self.auth_manager.test_connection()
        
        assert result is True
    
    def test_logout(self):
        """測試登出"""
        self.auth_manager._drive_service = Mock()
        self.auth_manager._service_cache['test'] = Mock()
        
        self.auth_manager.logout()
        
        self.mock_oauth_provider.revoke_credentials.assert_called_once()
        assert len(self.auth_manager._service_cache) == 0
        assert self.auth_manager._drive_service is None


if __name__ == '__main__':
    pytest.main([__file__]) 