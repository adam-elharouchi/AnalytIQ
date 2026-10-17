"""
tests/unit/test_self_service.py — self-service data export + account delete (FERPA/GDPR).
"""
import bcrypt

AUTH = {"X-Test-User-ID": "u1", "X-Test-User-Role": "student"}

# A real bcrypt hash for the password-confirmation tests (low rounds = fast).
_PW = "correct-horse-battery"
_PW_HASH = bcrypt.hashpw(_PW.encode(), bcrypt.gensalt(rounds=4)).decode()


class TestExportMyData:
    def test_returns_json_attachment(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.description = [
            ("user_id",),
            ("name",),
            ("email",),
            ("role",),
            ("account_status",),
            ("created_at",),
            ("last_login",),
        ]
        cursor.fetchall.return_value = [("u1", "Alice", "a@b.com", "student", "active", None, None)]
        resp = client.get("/api/users/export", headers=AUTH)
        assert resp.status_code == 200
        assert "attachment" in (resp.headers.get("Content-Disposition") or "")
        body = resp.get_json()
        assert body["account"]["email"] == "a@b.com"
        assert "exported_at" in body

    def test_unknown_user_returns_404(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.description = [("user_id",)]
        cursor.fetchall.return_value = []
        resp = client.get("/api/users/export", headers=AUTH)
        assert resp.status_code == 404

    def test_requires_auth(self, client, mock_db):
        assert client.get("/api/users/export").status_code == 401


class TestDeleteAccountCascade:
    def test_delete_returns_200(self, client, mock_db):
        resp = client.delete("/api/users/delete", headers=AUTH)
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_delete_removes_the_users_row(self, client, mock_db):
        """The handler deletes the users row and leaves the cascade to the schema.

        Every child table reaches users.user_id through an ON DELETE CASCADE, so
        the rows go with it. That is asserted against a real database -- not a
        mock -- by tests/integration/test_schema_constraints.py (every FK has a
        deliberate ON DELETE action) and the delete-path tests in
        tests/integration/test_superadmin.py and test_tenant_admin.py.
        """
        client.delete("/api/users/delete", headers=AUTH)
        executed = " ".join(str(c) for c in mock_db.cursor().execute.call_args_list)
        assert "DELETE FROM users" in executed

    def test_requires_auth(self, client, mock_db):
        assert client.delete("/api/users/delete").status_code == 401


class TestDeleteAccountPasswordConfirm:
    """A password-backed account must re-confirm its password; SSO accounts need not."""

    def test_sso_account_no_password_deletes(self, client, mock_db):
        # password_hash IS NULL (fetchone -> None) => SSO/LTI-only account.
        mock_db.cursor().fetchone.return_value = None
        resp = client.delete("/api/users/delete", headers=AUTH, json={})
        assert resp.status_code == 200

    def test_password_account_correct_password_deletes(self, client, mock_db):
        mock_db.cursor().fetchone.return_value = (_PW_HASH,)
        resp = client.delete("/api/users/delete", headers=AUTH, json={"password": _PW})
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_password_account_wrong_password_401(self, client, mock_db):
        mock_db.cursor().fetchone.return_value = (_PW_HASH,)
        resp = client.delete("/api/users/delete", headers=AUTH, json={"password": "nope"})
        assert resp.status_code == 401

    def test_password_account_missing_password_400(self, client, mock_db):
        mock_db.cursor().fetchone.return_value = (_PW_HASH,)
        resp = client.delete("/api/users/delete", headers=AUTH, json={})
        assert resp.status_code == 400

    def test_wrong_password_does_not_delete(self, client, mock_db):
        mock_db.cursor().fetchone.return_value = (_PW_HASH,)
        client.delete("/api/users/delete", headers=AUTH, json={"password": "nope"})
        executed = " ".join(str(c) for c in mock_db.cursor().execute.call_args_list)
        assert "DELETE FROM users" not in executed
