"""Tests for auth middleware."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vpn_simulator.api.middleware.auth import AuthMiddleware, PUBLIC_PATHS


@pytest.fixture
def app_with_auth():
    app = FastAPI()
    app.add_middleware(AuthMiddleware, api_key="test-key")

    @app.get("/protected")
    async def protected():
        return {"status": "ok"}

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    return app


@pytest.fixture
def app_no_auth():
    app = FastAPI()
    app.add_middleware(AuthMiddleware, api_key=None)

    @app.get("/protected")
    async def protected():
        return {"status": "ok"}

    return app


class TestPublicPaths:
    def test_public_paths_defined(self):
        assert "/health" in PUBLIC_PATHS
        assert "/docs" in PUBLIC_PATHS
        assert "/openapi.json" in PUBLIC_PATHS
        assert "/redoc" in PUBLIC_PATHS


class TestAuthMiddleware:
    def test_public_path_no_auth_required(self, app_with_auth):
        client = TestClient(app_with_auth)
        response = client.get("/health")
        assert response.status_code == 200

    def test_protected_path_no_key_returns_401(self, app_with_auth):
        client = TestClient(app_with_auth)
        response = client.get("/protected")
        assert response.status_code == 401

    def test_protected_path_wrong_key_returns_401(self, app_with_auth):
        client = TestClient(app_with_auth)
        response = client.get("/protected", headers={"X-API-Key": "wrong-key"})
        assert response.status_code == 401

    def test_protected_path_correct_key_returns_200(self, app_with_auth):
        client = TestClient(app_with_auth)
        response = client.get("/protected", headers={"X-API-Key": "test-key"})
        assert response.status_code == 200

    def test_no_auth_key_allows_all(self, app_no_auth):
        client = TestClient(app_no_auth)
        response = client.get("/protected")
        assert response.status_code == 200
