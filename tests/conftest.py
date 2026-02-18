"""
Pytest configuration and shared fixtures for AnalytIQ tests
"""
import pytest
import os
from unittest.mock import Mock, MagicMock
from datetime import datetime


# ============================================================================
# Environment Setup
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables"""
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost:5432/test_db'
    os.environ['REDIS_URL'] = 'redis://localhost:6379/1'
    os.environ['FEATURE_ASYNC_TASKS'] = 'False'
    os.environ['FEATURE_CACHING'] = 'False'
    os.environ['FEATURE_CSRF_PROTECTION'] = 'False'
    yield
    # Cleanup after all tests


# ============================================================================
# Flask App Fixtures
# ============================================================================

@pytest.fixture
def app():
    """Create minimal Flask app for testing"""
    # Set test environment before importing app
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['FEATURE_ASYNC_TASKS'] = 'False'
    os.environ['FEATURE_CACHING'] = 'False'
    os.environ['FEATURE_CSRF_PROTECTION'] = 'False'
    
    from app import app as flask_app
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    
    # Disable rate limiting in tests to avoid 429 errors
    try:
        from app import limiter
        if limiter:
            limiter.enabled = False
    except (ImportError, AttributeError):
        pass
    
    return flask_app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
def mock_db_cursor():
    """Mock database cursor"""
    cursor = MagicMock()
    cursor.fetchone = Mock(return_value=None)
    cursor.fetchall = Mock(return_value=[])
    cursor.execute = Mock()
    cursor.close = Mock()
    return cursor


@pytest.fixture
def mock_db_connection(mock_db_cursor):
    """Mock database connection"""
    conn = MagicMock()
    conn.cursor = Mock(return_value=mock_db_cursor)
    conn.commit = Mock()
    conn.rollback = Mock()
    conn.close = Mock()
    return conn


@pytest.fixture
def mock_db(mock_db_connection, monkeypatch):
    """Mock database for testing - patches get_db_connection in all modules."""
    def mock_get_db():
        return mock_db_connection

    # Patch in the canonical location (db module) so all blueprints get the mock
    monkeypatch.setattr('db.get_db_connection', mock_get_db)
    # Patch blueprint modules so their imported reference is also mocked
    for module in [
        'blueprints.auth',
        'blueprints.users',
        'blueprints.health',
        'blueprints.ai',
        'blueprints.chapters',
        'blueprints.exercises',
        'blueprints.classes',
    ]:
        try:
            monkeypatch.setattr(f'{module}.get_db_connection', mock_get_db)
        except AttributeError:
            pass  # module doesn't use get_db_connection

    return mock_db_connection



# ============================================================================
# Redis Fixtures
# ============================================================================

@pytest.fixture
def mock_redis_client():
    """Mock Redis client"""
    redis_mock = MagicMock()
    redis_mock.get = Mock(return_value=None)
    redis_mock.set = Mock(return_value=True)
    redis_mock.setex = Mock(return_value=True)
    redis_mock.delete = Mock(return_value=1)
    redis_mock.keys = Mock(return_value=[])
    redis_mock.ping = Mock(return_value=True)
    redis_mock.info = Mock(return_value={
        'total_connections_received': 10,
        'total_commands_processed': 100,
        'keyspace_hits': 80,
        'keyspace_misses': 20
    })
    return redis_mock


# ============================================================================
# Supabase Fixtures
# ============================================================================

@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client"""
    supabase_mock = MagicMock()
    
    # Mock storage operations
    storage_mock = MagicMock()
    storage_mock.upload = Mock(return_value={'path': 'test.pdf'})
    storage_mock.get_public_url = Mock(return_value='https://test.supabase.co/storage/test.pdf')
    storage_mock.create_signed_url = Mock(return_value={'signedURL': 'https://test.supabase.co/signed/test.pdf'})
    storage_mock.remove = Mock(return_value=True)
    storage_mock.list = Mock(return_value=[])
    
    supabase_mock.storage.from_ = Mock(return_value=storage_mock)
    
    return supabase_mock


# ============================================================================
# Celery Fixtures
# ============================================================================

@pytest.fixture
def mock_celery_app():
    """Mock Celery application"""
    celery_mock = MagicMock()
    celery_mock.conf.broker_url = 'redis://localhost:6379/0'
    celery_mock.conf.result_backend = 'redis://localhost:6379/0'
    celery_mock.tasks = {}
    return celery_mock


@pytest.fixture
def mock_celery_task():
    """Mock Celery task"""
    task_mock = MagicMock()
    task_mock.apply_async = Mock(return_value=MagicMock(id='test-task-id'))
    task_mock.delay = Mock(return_value=MagicMock(id='test-task-id'))
    return task_mock


# ============================================================================
# Flask Fixtures
# ============================================================================

@pytest.fixture
def mock_flask_request():
    """Mock Flask request object"""
    request_mock = MagicMock()
    request_mock.args = {}
    request_mock.json = {}
    request_mock.form = {}
    request_mock.files = {}
    request_mock.headers = {}
    request_mock.method = 'GET'
    return request_mock


# ============================================================================
# Data Fixtures
# ============================================================================

@pytest.fixture
def sample_user():
    """Sample user data"""
    return {
        'user_id': 'test-user-123',
        'email': 'test@example.com',
        'name': 'Test User',
        'role': 'student',
        'created_at': datetime.now()
    }


@pytest.fixture
def sample_class():
    """Sample class data"""
    return {
        'class_id': 'test-class-123',
        'class_name': 'Test Class',
        'class_code': 'TEST101',
        'professor_id': 'prof-123',
        'created_at': datetime.now()
    }


@pytest.fixture
def sample_chapter():
    """Sample chapter data"""
    return {
        'chapter_id': 'test-chapter-123',
        'class_id': 'test-class-123',
        'title': 'Test Chapter',
        'pdf_filename': 'test.pdf',
        'pdf_url': 'https://test.supabase.co/storage/test.pdf',
        'created_at': datetime.now()
    }


@pytest.fixture
def sample_pdf_bytes():
    """Sample PDF file bytes"""
    # Minimal valid PDF header
    return b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n%%EOF'


# ============================================================================
# Pagination Fixtures
# ============================================================================

@pytest.fixture
def pagination_params():
    """Sample pagination parameters"""
    return {
        'limit': 10,
        'offset': 0
    }


@pytest.fixture
def pagination_metadata():
    """Sample pagination metadata"""
    return {
        'total': 100,
        'limit': 10,
        'offset': 0,
        'has_more': True,
        'current_page': 1,
        'total_pages': 10
    }
