"""
tests/unit/test_self_service.py — self-service data export + account delete (FERPA/GDPR).
"""
AUTH = {"X-Test-User-ID": "u1", "X-Test-User-Role": "student"}


class TestExportMyData:
    def test_returns_json_attachment(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.description = [
            ("user_id",), ("name",), ("email",), ("role",),
            ("account_status",), ("created_at",), ("last_login",),
        ]
        cursor.fetchall.return_value = [
            ("u1", "Alice", "a@b.com", "student", "active", None, None)
        ]
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

    def test_delete_cascades_child_tables(self, client, mock_db):
        client.delete("/api/users/delete", headers=AUTH)
        executed = " ".join(str(c) for c in mock_db.cursor().execute.call_args_list)
        assert "class_enrollments" in executed
        assert "practice_progress" in executed
        assert "DELETE FROM users" in executed

    def test_requires_auth(self, client, mock_db):
        assert client.delete("/api/users/delete").status_code == 401
