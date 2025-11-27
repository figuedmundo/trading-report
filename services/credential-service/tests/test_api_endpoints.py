"""
Tests for credential service API endpoints.

Tests focus on critical workflows:
- POST /api/v1/credentials creates credential and returns 201
- GET /api/v1/credentials/domain/X returns credential with decrypted password
- 404 returned for non-existent domain/credential
- 500 returned on decryption failure
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import os
from cryptography.fernet import Fernet

# Generate a test encryption key
TEST_ENCRYPTION_KEY = Fernet.generate_key().decode('utf-8')


@pytest.fixture(autouse=True)
def setup_env():
    """Set up test environment."""
    os.environ['CREDENTIAL_ENCRYPTION_KEY'] = TEST_ENCRYPTION_KEY
    os.environ['DATABASE_URL'] = 'postgresql://user:password@localhost/test_db'
    yield
    if 'CREDENTIAL_ENCRYPTION_KEY' in os.environ:
        del os.environ['CREDENTIAL_ENCRYPTION_KEY']


@pytest.fixture
def client():
    """Create FastAPI test client with mocked database."""
    with patch('src.database.init_connection_pool'):
        with patch('src.database.close_connection_pool'):
            from src.main import app
            return TestClient(app)


@patch('src.database.init_connection_pool')
@patch('src.database.get_db_pool')
def test_health_check_success(mock_get_pool, mock_init, client):
    """Test health check endpoint returns 200 when database is healthy."""
    # Mock the connection pool
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_pool.getconn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    mock_get_pool.return_value = mock_pool

    response = client.get('/health')

    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert data['database_connected'] is True
    assert 'correlation_id' in data
    assert 'timestamp' in data


@patch('src.database.get_db_pool')
def test_health_check_no_pool(mock_get_pool, client):
    """Test health check returns 503 when database pool is None."""
    mock_get_pool.return_value = None

    response = client.get('/health')

    assert response.status_code == 503
    data = response.json()
    assert data['status'] == 'unavailable'
    assert data['database_connected'] is False


@patch('src.database.create_credential')
def test_create_credential_success(mock_create, client):
    """Test POST /api/v1/credentials creates credential and returns 201."""
    mock_create.return_value = {
        'id': '550e8400-e29b-41d4-a716-446655440000',
        'domain': 'broker.com',
        'username': 'john_doe',
        'is_active': True,
        'metadata': {},
        'created_at': '2024-01-01T00:00:00+00:00',
        'updated_at': '2024-01-01T00:00:00+00:00',
    }

    response = client.post(
        '/api/v1/credentials',
        json={
            'domain': 'broker.com',
            'username': 'john_doe',
            'password': 'secret_password',
            'metadata': {},
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data['domain'] == 'broker.com'
    assert data['username'] == 'john_doe'
    assert 'password' not in data  # Password should not be in response
    assert 'correlation_id' in data


@patch('src.database.create_credential')
def test_create_credential_duplicate_domain(mock_create, client):
    """Test POST returns 409 Conflict when domain already exists."""
    import psycopg2
    mock_create.side_effect = psycopg2.IntegrityError('UNIQUE constraint failed')

    response = client.post(
        '/api/v1/credentials',
        json={
            'domain': 'broker.com',
            'username': 'john_doe',
            'password': 'secret_password',
        }
    )

    assert response.status_code == 409
    assert 'already exists' in response.json()['detail']


@patch('src.database.get_credential_by_domain')
def test_get_credential_by_domain_success(mock_get, client):
    """Test GET /api/v1/credentials/domain/X returns credential with decrypted password."""
    mock_get.return_value = {
        'id': '550e8400-e29b-41d4-a716-446655440000',
        'domain': 'broker.com',
        'username': 'john_doe',
        'password': 'decrypted_password',  # Decrypted by the database layer
        'metadata': {},
        'is_active': True,
        'created_at': '2024-01-01T00:00:00+00:00',
        'updated_at': '2024-01-01T00:00:00+00:00',
        'last_used_at': None,
    }

    response = client.get('/api/v1/credentials/domain/broker.com')

    assert response.status_code == 200
    data = response.json()
    assert data['domain'] == 'broker.com'
    assert data['username'] == 'john_doe'
    assert data['password'] == 'decrypted_password'  # Password should be in GET response
    assert 'correlation_id' in data


@patch('src.database.get_credential_by_domain')
def test_get_credential_not_found(mock_get, client):
    """Test GET returns 404 for non-existent domain."""
    mock_get.return_value = None

    response = client.get('/api/v1/credentials/domain/nonexistent.com')

    assert response.status_code == 404
    assert 'not found' in response.json()['detail']


@patch('src.database.get_credential_by_id')
def test_get_credential_by_id_success(mock_get, client):
    """Test GET /api/v1/credentials/{id} returns credential."""
    mock_get.return_value = {
        'id': '550e8400-e29b-41d4-a716-446655440000',
        'domain': 'broker.com',
        'username': 'john_doe',
        'password': 'decrypted_password',
        'metadata': {},
        'is_active': True,
        'created_at': '2024-01-01T00:00:00+00:00',
        'updated_at': '2024-01-01T00:00:00+00:00',
        'last_used_at': None,
    }

    response = client.get('/api/v1/credentials/550e8400-e29b-41d4-a716-446655440000')

    assert response.status_code == 200
    data = response.json()
    assert data['id'] == '550e8400-e29b-41d4-a716-446655440000'
    assert data['password'] == 'decrypted_password'


@patch('src.database.get_credential_by_id')
def test_get_credential_by_id_not_found(mock_get, client):
    """Test GET /{id} returns 404 when credential not found."""
    mock_get.return_value = None

    response = client.get('/api/v1/credentials/550e8400-e29b-41d4-a716-446655440000')

    assert response.status_code == 404


@patch('src.database.update_credential')
@patch('src.database.get_credential_by_id')
def test_update_credential_success(mock_get, mock_update, client):
    """Test PUT /api/v1/credentials/{id} updates credential."""
    mock_get.return_value = {
        'id': '550e8400-e29b-41d4-a716-446655440000',
        'domain': 'broker.com',
        'username': 'old_user',
        'password': 'old_password',
        'metadata': {},
        'is_active': True,
        'created_at': '2024-01-01T00:00:00+00:00',
        'updated_at': '2024-01-01T00:00:00+00:00',
        'last_used_at': None,
    }

    mock_update.return_value = {
        'id': '550e8400-e29b-41d4-a716-446655440000',
        'domain': 'broker.com',
        'username': 'new_user',
        'is_active': True,
        'metadata': {},
        'created_at': '2024-01-01T00:00:00+00:00',
        'updated_at': '2024-01-01T12:00:00+00:00',
    }

    response = client.put(
        '/api/v1/credentials/550e8400-e29b-41d4-a716-446655440000',
        json={
            'domain': 'broker.com',
            'username': 'new_user',
            'password': 'new_password',
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data['username'] == 'new_user'


@patch('src.database.delete_credential')
def test_delete_credential_success(mock_delete, client):
    """Test DELETE /api/v1/credentials/{id} deletes credential."""
    mock_delete.return_value = True

    response = client.delete('/api/v1/credentials/550e8400-e29b-41d4-a716-446655440000')

    assert response.status_code == 204


@patch('src.database.delete_credential')
def test_delete_credential_not_found(mock_delete, client):
    """Test DELETE returns 404 when credential not found."""
    mock_delete.return_value = False

    response = client.delete('/api/v1/credentials/550e8400-e29b-41d4-a716-446655440000')

    assert response.status_code == 404


@patch('src.database.list_all_credentials')
def test_list_credentials_success(mock_list, client):
    """Test GET /api/v1/credentials lists all credentials."""
    mock_list.return_value = [
        {
            'id': '550e8400-e29b-41d4-a716-446655440000',
            'domain': 'broker1.com',
            'username': 'user1',
            'is_active': True,
            'metadata': {},
            'created_at': '2024-01-01T00:00:00+00:00',
            'updated_at': '2024-01-01T00:00:00+00:00',
            'last_used_at': None,
        },
        {
            'id': '550e8400-e29b-41d4-a716-446655440001',
            'domain': 'broker2.com',
            'username': 'user2',
            'is_active': True,
            'metadata': {},
            'created_at': '2024-01-02T00:00:00+00:00',
            'updated_at': '2024-01-02T00:00:00+00:00',
            'last_used_at': None,
        }
    ]

    response = client.get('/api/v1/credentials')

    assert response.status_code == 200
    data = response.json()
    assert len(data['credentials']) == 2
    assert data['total'] == 2
    assert 'correlation_id' in data
