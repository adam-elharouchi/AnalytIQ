import json
import pytest
from app import app
from db import get_db_connection

# Generate a super admin token for testing
def get_super_admin_token(client):
    from auth_helpers import create_jwt_token
    # In test context we can just generate one directly
    token = create_jwt_token("sah_123", role="superadmin", name="Super Admin", email="admin@hult.edu")
    return token

def get_normal_token(client):
    from auth_helpers import create_jwt_token
    token = create_jwt_token("norm_123", role="student", name="Normal User", email="student@student.hult.edu")
    return token

@pytest.fixture
def super_admin_headers(client):
    return {"Authorization": f"Bearer {get_super_admin_token(client)}"}

@pytest.fixture
def normal_headers(client):
    return {"Authorization": f"Bearer {get_normal_token(client)}"}

def test_tenant_api_access(client, super_admin_headers, normal_headers, tx):
    # Standard user cannot access
    res = client.get("/api/superadmin/tenants", headers=normal_headers)
    assert res.status_code == 403

    # Super admin can access
    res = client.get("/api/superadmin/tenants", headers=super_admin_headers)
    assert res.status_code == 200
    assert "tenants" in res.json

def test_tenant_creation(client, super_admin_headers, tx):
    # Create new tenant
    data = {
        "name": "Test University",
        "lti_issuer": "https://canvas.test.edu"
    }
    res = client.post("/api/superadmin/tenants", headers=super_admin_headers, json=data)
    assert res.status_code == 201
    assert res.json["tenant"]["name"] == "Test University"
    
    tenant_id = res.json["tenant"]["tenant_id"]

    # Toggle Active Status
    patch_data = {"is_active": False}
    res = client.patch(f"/api/superadmin/tenants/{tenant_id}", headers=super_admin_headers, json=patch_data)
    assert res.status_code == 200

def test_impersonation(client, super_admin_headers, tx):
    from repositories import auth_repository as auth_repo
    from auth_helpers import hash_password
    
    auth_repo.insert_user(tx, 'inttest_imp_target', 'Imp Target', 'imp@example.com', hash_password('password'), 'student')

    res = client.post("/api/superadmin/users/inttest_imp_target/impersonate", headers=super_admin_headers)
    assert res.status_code == 200
    token = res.json["token"]
    assert token is not None

    # Verify impersonation embedded attributes
    from auth_helpers import decode_jwt_token
    payload = decode_jwt_token(token)
    assert payload["user_id"] == "inttest_imp_target"
    assert payload["role"] == "student"
    assert payload["impersonator_id"] == "sah_123"

def test_user_search(client, super_admin_headers, tx):
    res = client.get("/api/superadmin/users?q=Admin", headers=super_admin_headers)
    print("USER SEARCH RESPONSE:", res.data)
    assert res.status_code == 200
    assert "users" in res.json
    assert "total" in res.json
