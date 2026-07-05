"""
tests/unit/test_sso_exchange.py — SSO one-time-code token delivery.

The callback stores the token pair under a single-use code and redirects with
?sso_code=; POST /api/sso/exchange redeems it. Tokens never appear in the URL.
"""
import blueprints.sso as sso


class TestSsoExchangeEndpoint:
    def test_missing_code_returns_400(self, client, mock_db):
        assert client.post("/api/sso/exchange", json={}).status_code == 400

    def test_unknown_code_returns_400(self, client, mock_db, monkeypatch):
        monkeypatch.setattr("blueprints.sso._pop_sso_code", lambda c: None)
        assert client.post("/api/sso/exchange", json={"code": "abc"}).status_code == 400

    def test_valid_code_returns_token_pair(self, client, mock_db, monkeypatch):
        monkeypatch.setattr(
            "blueprints.sso._pop_sso_code",
            lambda c: {"token": "ACCESS", "refresh_token": "REFRESH"},
        )
        r = client.post("/api/sso/exchange", json={"code": "abc"})
        assert r.status_code == 200
        data = r.get_json()
        assert data["token"] == "ACCESS"
        assert data["refresh_token"] == "REFRESH"


class TestSsoCodeStorePop:
    def test_roundtrip_is_single_use(self, monkeypatch):
        store = {}

        class FakeRedis:
            def setex(self, k, ttl, v):
                store[k] = v

            def get(self, k):
                return store.get(k)

            def delete(self, k):
                store.pop(k, None)

        monkeypatch.setattr("core.cache.redis_client", FakeRedis())
        assert sso._store_sso_code("code1", {"token": "T", "refresh_token": "R"}) is True
        assert sso._pop_sso_code("code1") == {"token": "T", "refresh_token": "R"}
        # Second redemption fails — the code is single-use.
        assert sso._pop_sso_code("code1") is None

    def test_store_returns_false_without_redis(self, monkeypatch):
        monkeypatch.setattr("core.cache.redis_client", None)
        assert sso._store_sso_code("code2", {"token": "T"}) is False
