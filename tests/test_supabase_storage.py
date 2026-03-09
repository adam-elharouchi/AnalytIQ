"""
Unit tests for Supabase Storage utilities (supabase_storage.py) - FIXED VERSION
"""
import pytest
from unittest.mock import Mock, patch, MagicMock


class TestUploadPDF:
    """Tests for upload_pdf function"""
    
    @patch('supabase_storage.supabase')
    def test_upload_success(self, mock_supabase):
        """Test successful PDF upload"""
        from supabase_storage import upload_pdf
        
        # Mock successful upload
        mock_storage = MagicMock()
        mock_storage.upload.return_value = {'path': 'test.pdf'}
        mock_storage.get_public_url.return_value = 'https://test.supabase.co/storage/test.pdf'
        mock_supabase.storage.from_.return_value = mock_storage
        
        pdf_bytes = b'%PDF-1.4 test content'
        result = upload_pdf(pdf_bytes, 'test.pdf')
        
        assert result == 'https://test.supabase.co/storage/test.pdf'
        mock_storage.upload.assert_called_once()
    
    @patch('supabase_storage.supabase', None)
    def test_upload_no_client(self):
        """Test upload when Supabase client not initialized"""
        from supabase_storage import upload_pdf
        
        with pytest.raises(ValueError, match="Supabase client not initialized"):
            upload_pdf(b'test', 'test.pdf')
    
    @patch('supabase_storage.supabase')
    def test_upload_failure(self, mock_supabase):
        """Test upload failure handling"""
        from supabase_storage import upload_pdf
        
        # Mock upload failure
        mock_storage = MagicMock()
        mock_storage.upload.side_effect = Exception('Upload failed')
        mock_supabase.storage.from_.return_value = mock_storage
        
        result = upload_pdf(b'test', 'test.pdf')
        
        assert result is None


class TestGetPDFURL:
    """Tests for get_pdf_url function"""
    
    @patch('supabase_storage.supabase')
    def test_get_signed_url(self, mock_supabase):
        """Test getting signed PDF URL"""
        from supabase_storage import get_pdf_url
        
        mock_storage = MagicMock()
        mock_storage.create_signed_url.return_value = {
            'signedURL': 'https://test.supabase.co/signed/test.pdf'
        }
        mock_supabase.storage.from_.return_value = mock_storage
        
        result = get_pdf_url('test.pdf', expires_in=3600)
        
        assert result == 'https://test.supabase.co/signed/test.pdf'
        mock_storage.create_signed_url.assert_called_once()
    
    @patch('supabase_storage.supabase', None)
    def test_get_url_no_client(self):
        """Test get URL when client not initialized"""
        from supabase_storage import get_pdf_url
        
        with pytest.raises(ValueError, match="Supabase client not initialized"):
            get_pdf_url('test.pdf')
    
    @patch('supabase_storage.supabase')
    def test_get_url_failure(self, mock_supabase):
        """Test URL generation failure"""
        from supabase_storage import get_pdf_url
        
        mock_storage = MagicMock()
        mock_storage.create_signed_url.side_effect = Exception('URL generation failed')
        mock_supabase.storage.from_.return_value = mock_storage
        
        result = get_pdf_url('test.pdf')
        
        assert result is None


class TestDeletePDF:
    """Tests for delete_pdf function"""
    
    @patch('supabase_storage.supabase')
    def test_delete_success(self, mock_supabase):
        """Test successful PDF deletion"""
        from supabase_storage import delete_pdf
        
        mock_storage = MagicMock()
        mock_storage.remove.return_value = True
        mock_supabase.storage.from_.return_value = mock_storage
        
        result = delete_pdf('test.pdf')
        
        assert result is True
        mock_storage.remove.assert_called_once_with(['test.pdf'])
    
    @patch('supabase_storage.supabase')
    def test_delete_failure(self, mock_supabase):
        """Test deletion failure handling"""
        from supabase_storage import delete_pdf
        
        mock_storage = MagicMock()
        mock_storage.remove.side_effect = Exception('Delete failed')
        mock_supabase.storage.from_.return_value = mock_storage
        
        result = delete_pdf('test.pdf')
        
        assert result is False
    
    @patch('supabase_storage.supabase', None)
    def test_delete_no_client(self):
        """Test delete when client not initialized"""
        from supabase_storage import delete_pdf
        
        with pytest.raises(ValueError, match="Supabase client not initialized"):
            delete_pdf('test.pdf')


class TestMigratePDFFromDB:
    """Tests for migrate_pdf_from_db function"""
    
    @patch('supabase_storage.upload_pdf')
    @patch('supabase_storage.supabase')
    def test_migrate_success(self, mock_supabase, mock_upload):
        """Test successful PDF migration"""
        from supabase_storage import migrate_pdf_from_db
        
        mock_upload.return_value = 'https://test.supabase.co/storage/test.pdf'
        
        pdf_data = b'%PDF-1.4 test'
        result = migrate_pdf_from_db('chapter-123', pdf_data, 'test.pdf')
        
        assert result['success'] is True
        assert result['url'] == 'https://test.supabase.co/storage/test.pdf'
        assert 'filename' in result
        assert result['error'] is None
    
    @patch('supabase_storage.upload_pdf')
    @patch('supabase_storage.supabase')
    def test_migrate_upload_failure(self, mock_supabase, mock_upload):
        """Test migration when upload fails"""
        from supabase_storage import migrate_pdf_from_db
        
        mock_upload.return_value = None
        
        result = migrate_pdf_from_db('chapter-123', b'test', 'test.pdf')
        
        assert result['success'] is False
        assert result['url'] is None
        assert 'Upload failed' in result['error']
    
    @patch('supabase_storage.supabase', None)
    def test_migrate_no_client(self):
        """Test migration when Supabase not initialized"""
        from supabase_storage import migrate_pdf_from_db
        
        result = migrate_pdf_from_db('chapter-123', b'test', 'test.pdf')
        
        assert result['success'] is False
        assert 'not initialized' in result['error']


class TestStorageHealthCheck:
    """Tests for storage_health_check function"""
    
    @patch('supabase_storage.supabase')
    def test_health_check_healthy(self, mock_supabase):
        """Test health check when storage is accessible"""
        from supabase_storage import storage_health_check
        
        mock_supabase.storage.from_.return_value.list.return_value = []
        
        result = storage_health_check()
        assert result['healthy'] is True
        assert 'accessible' in result['message']

    @patch('supabase_storage.supabase', None)
    def test_health_check_no_client(self):
        """Test health check when client not initialized"""
        from supabase_storage import storage_health_check
        
        result = storage_health_check()
        assert result['healthy'] is False
        assert 'not initialized' in result['message']

    @patch('supabase_storage.supabase')
    def test_health_check_connection_error(self, mock_supabase):
        """Test health check when connection fails"""
        from supabase_storage import storage_health_check
        
        mock_supabase.storage.from_.side_effect = Exception("Connection refused")
        
        result = storage_health_check()
        assert result['healthy'] is False
        assert result['message']  # non-empty message
