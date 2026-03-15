import sys
from core.auth import create_jwt_token
print(create_jwt_token("test-superadmin-id", "superadmin", "Test Admin", "superadmin@myanalytiq.org"))
