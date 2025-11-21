"""
檔案處理器測試
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

sys.path.append(str(Path(__file__).parent.parent))

from src.core.file_handler import (
    GoogleFileConverter,
    FileHandler,
    file_handler
)
from src.utils.exceptions import (
    FileNotFoundError,
    FilePermissionError,
    NetworkError,
    ValidationError
)


class TestGoogleFileConverter:
    """測試 Google Workspace 檔案轉換器"""

    def setup_method(self):
        """測試前設定"""
        self.converter = GoogleFileConverter()

    def test_init(self):
        """測試初始化"""
        converter = GoogleFileConverter()
        assert converter is not None

    def test_get_export_format_docs_default(self):
        """測試 Google Docs 預設轉換格式"""
        mime_type = 'application/vnd.google-apps.document'
        result = self.converter.get_export_format(mime_type)

        # 預設應該是 docx (Word 格式)
        assert result == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'

    def test_get_export_format_sheets_default(self):
        """測試 Google Sheets 預設轉換格式"""
        mime_type = 'application/vnd.google-apps.spreadsheet'
        result = self.converter.get_export_format(mime_type)

        # 預設應該是 xlsx (Excel 格式)
        assert result == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    def test_get_export_format_slides_default(self):
        """測試 Google Slides 預設轉換格式"""
        mime_type = 'application/vnd.google-apps.presentation'
        result = self.converter.get_export_format(mime_type)

        # 預設應該是 pptx (PowerPoint 格式)
        assert result == 'application/vnd.openxmlformats-officedocument.presentationml.presentation'

    def test_get_export_format_drawing_default(self):
        """測試 Google Drawing 預設轉換格式"""
        mime_type = 'application/vnd.google-apps.drawing'
        result = self.converter.get_export_format(mime_type)

        # 預設應該是 png
        assert result == 'image/png'

    def test_get_export_format_docs_preferred_pdf(self):
        """測試 Google Docs 指定 PDF 格式"""
        mime_type = 'application/vnd.google-apps.document'
        result = self.converter.get_export_format(mime_type, preferred_format='pdf')

        assert result == 'application/pdf'

    def test_get_export_format_sheets_preferred_csv(self):
        """測試 Google Sheets 指定 CSV 格式"""
        mime_type = 'application/vnd.google-apps.spreadsheet'
        result = self.converter.get_export_format(mime_type, preferred_format='csv')

        assert result == 'text/csv'

    def test_get_export_format_unknown_mime_type(self):
        """測試不支援的 MIME 類型"""
        mime_type = 'application/unknown'
        result = self.converter.get_export_format(mime_type)

        assert result is None

    def test_get_office_format_name_docs(self):
        """測試 Office 格式名稱 - 文件"""
        mime_type = 'application/vnd.google-apps.document'
        result = self.converter.get_office_format_name(mime_type)

        assert 'Word' in result
        assert '.docx' in result

    def test_get_office_format_name_sheets(self):
        """測試 Office 格式名稱 - 試算表"""
        mime_type = 'application/vnd.google-apps.spreadsheet'
        result = self.converter.get_office_format_name(mime_type)

        assert 'Excel' in result
        assert '.xlsx' in result

    def test_get_office_format_name_slides(self):
        """測試 Office 格式名稱 - 簡報"""
        mime_type = 'application/vnd.google-apps.presentation'
        result = self.converter.get_office_format_name(mime_type)

        assert 'PowerPoint' in result
        assert '.pptx' in result

    def test_get_office_format_name_unknown(self):
        """測試未知格式名稱"""
        mime_type = 'application/unknown'
        result = self.converter.get_office_format_name(mime_type)

        assert '未知' in result

    def test_get_export_extension_docs(self):
        """測試匯出副檔名 - 文件"""
        mime_type = 'application/vnd.google-apps.document'
        export_format = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        result = self.converter.get_export_extension(mime_type, export_format)

        assert result == '.docx'

    def test_get_export_extension_sheets(self):
        """測試匯出副檔名 - 試算表"""
        mime_type = 'application/vnd.google-apps.spreadsheet'
        export_format = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        result = self.converter.get_export_extension(mime_type, export_format)

        assert result == '.xlsx'

    def test_get_export_extension_pdf(self):
        """測試匯出副檔名 - PDF"""
        mime_type = 'application/vnd.google-apps.document'
        export_format = 'application/pdf'
        result = self.converter.get_export_extension(mime_type, export_format)

        assert result == '.pdf'


class TestFileHandler:
    """測試檔案處理器"""

    def setup_method(self):
        """測試前設定"""
        self.mock_drive_service = Mock()
        self.handler = FileHandler(drive_service=self.mock_drive_service)

    def test_init(self):
        """測試初始化"""
        handler = FileHandler()
        assert handler.drive_service is None
        assert handler.converter is not None
        assert handler.retry_manager is not None

    def test_init_with_drive_service(self):
        """測試帶 Drive 服務的初始化"""
        mock_service = Mock()
        handler = FileHandler(drive_service=mock_service)

        assert handler.drive_service == mock_service

    def test_get_drive_service_creates_new(self):
        """測試取得 Drive 服務 - 建立新服務"""
        handler = FileHandler()

        with patch('src.core.file_handler.get_authenticated_service') as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service

            result = handler._get_drive_service()

            assert result == mock_service
            mock_get_service.assert_called_once_with('drive')

    def test_get_drive_service_uses_existing(self):
        """測試取得 Drive 服務 - 使用現有服務"""
        result = self.handler._get_drive_service()

        assert result == self.mock_drive_service

    def test_get_file_info_invalid_id(self):
        """測試取得檔案資訊 - 無效 ID"""
        with pytest.raises(ValidationError):
            self.handler.get_file_info("")

    @patch('src.core.file_handler.ensure_authenticated')
    def test_get_file_info_success(self, mock_auth):
        """測試取得檔案資訊 - 成功"""
        mock_auth.return_value = lambda f: f

        file_info = {
            'id': 'test_id',
            'name': 'test_file.txt',
            'mimeType': 'text/plain',
            'size': '1024'
        }

        mock_execute = Mock(return_value=file_info)
        mock_get = Mock(return_value=Mock(execute=mock_execute))
        self.mock_drive_service.files.return_value.get = mock_get

        # 模擬 _safe_api_call 直接返回結果
        with patch.object(self.handler, '_safe_api_call', return_value=file_info):
            result = self.handler.get_file_info('test_id_123456')

        assert result == file_info

    def test_get_folder_contents_invalid_id(self):
        """測試取得資料夾內容 - 無效 ID"""
        with pytest.raises(ValidationError):
            self.handler.get_folder_contents("")

    def test_get_folder_contents_max_depth_exceeded(self):
        """測試取得資料夾內容 - 超過最大深度"""
        result = self.handler.get_folder_contents(
            'valid_folder_id_123',
            recursive=True,
            max_depth=5,
            current_depth=6
        )

        assert result == []

    def test_generate_safe_filename_basic(self):
        """測試生成安全檔案名稱 - 基本"""
        file_info = {
            'name': 'test file.txt',
            'mimeType': 'text/plain'
        }

        result = self.handler.generate_safe_filename(file_info)

        # 應該生成安全的檔案名稱
        assert result is not None
        assert len(result) > 0

    def test_generate_safe_filename_google_docs(self):
        """測試生成安全檔案名稱 - Google Docs"""
        file_info = {
            'name': 'My Document',
            'mimeType': 'application/vnd.google-apps.document'
        }

        result = self.handler.generate_safe_filename(file_info)

        # 應該添加 .docx 副檔名
        assert result.endswith('.docx')

    def test_generate_safe_filename_google_sheets(self):
        """測試生成安全檔案名稱 - Google Sheets"""
        file_info = {
            'name': 'My Spreadsheet',
            'mimeType': 'application/vnd.google-apps.spreadsheet'
        }

        result = self.handler.generate_safe_filename(file_info)

        # 應該添加 .xlsx 副檔名
        assert result.endswith('.xlsx')

    def test_generate_safe_filename_google_slides(self):
        """測試生成安全檔案名稱 - Google Slides"""
        file_info = {
            'name': 'My Presentation',
            'mimeType': 'application/vnd.google-apps.presentation'
        }

        result = self.handler.generate_safe_filename(file_info)

        # 應該添加 .pptx 副檔名
        assert result.endswith('.pptx')

    def test_save_file(self):
        """測試儲存檔案"""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / 'test_file.txt'
            content = b'test content'

            self.handler.save_file(content, file_path)

            assert file_path.exists()
            assert file_path.read_bytes() == content

    def test_save_file_creates_directory(self):
        """測試儲存檔案 - 建立目錄"""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / 'nested' / 'dir' / 'test_file.txt'
            content = b'test content'

            self.handler.save_file(content, file_path)

            assert file_path.exists()
            assert file_path.read_bytes() == content

    def test_get_download_stats(self):
        """測試取得下載統計"""
        file_list = [
            {'name': 'file1.txt', 'mimeType': 'text/plain', 'size': '1024'},
            {'name': 'file2.txt', 'mimeType': 'text/plain', 'size': '2048'},
            {'name': 'doc.gdoc', 'mimeType': 'application/vnd.google-apps.document'},
            {'name': 'folder', 'mimeType': 'application/vnd.google-apps.folder'},
        ]

        stats = self.handler.get_download_stats(file_list)

        assert stats['total_files'] == 4
        assert stats['total_size'] == 3072  # 1024 + 2048
        assert stats['google_workspace_files'] == 1
        assert stats['regular_files'] == 3
        assert 'file_types' in stats

    def test_get_download_stats_empty_list(self):
        """測試取得下載統計 - 空列表"""
        stats = self.handler.get_download_stats([])

        assert stats['total_files'] == 0
        assert stats['total_size'] == 0
        assert stats['google_workspace_files'] == 0

    def test_get_folder_contents_lite_invalid_id(self):
        """測試輕量級載入 - 無效 ID"""
        with pytest.raises(ValidationError):
            self.handler.get_folder_contents_lite("")


class TestGlobalFileHandler:
    """測試全域檔案處理器實例"""

    def test_global_file_handler_exists(self):
        """測試全域實例存在"""
        assert file_handler is not None
        assert isinstance(file_handler, FileHandler)


class TestFileHandlerConverterIntegration:
    """測試檔案處理器與轉換器的整合"""

    def setup_method(self):
        """測試前設定"""
        self.handler = FileHandler()

    @pytest.mark.parametrize("mime_type,expected_ext", [
        ('application/vnd.google-apps.document', '.docx'),
        ('application/vnd.google-apps.spreadsheet', '.xlsx'),
        ('application/vnd.google-apps.presentation', '.pptx'),
        ('application/vnd.google-apps.drawing', '.png'),
    ])
    def test_generate_safe_filename_for_google_types(self, mime_type, expected_ext):
        """測試不同 Google 類型的檔案名稱生成"""
        file_info = {
            'name': 'Test File',
            'mimeType': mime_type
        }

        result = self.handler.generate_safe_filename(file_info)

        assert result.endswith(expected_ext)


if __name__ == '__main__':
    pytest.main([__file__])
