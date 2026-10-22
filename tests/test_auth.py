import pytest
from httpx import AsyncClient


class TestAuth:
    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        response = await client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "running"

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "password123",
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert data["role"].lower() == "partner"
        assert data["partner_id"] is None
        assert "id" in data

    @pytest.mark.asyncio
    async def test_register_role_admin_ignored(self, client: AsyncClient):
        """Регрессия 1.1: role из запроса должен игнорироваться."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "hacker",
                "email": "hacker@example.com",
                "password": "password123",
                "role": "admin",
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["role"].lower() == "partner"

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={
                "username": "duplicate",
                "email": "dup1@example.com",
                "password": "password123",
            }
        )
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "duplicate",
                "email": "dup2@example.com",
                "password": "password123",
            }
        )
        assert response.status_code == 400
        assert "already taken" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={
                "username": "user1",
                "email": "same@example.com",
                "password": "password123",
            }
        )
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "user2",
                "email": "same@example.com",
                "password": "password123",
            }
        )
        assert response.status_code == 400
        assert "already taken" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={
                "username": "loginuser",
                "email": "login@example.com",
                "password": "test123",
            }
        )
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "loginuser",
                "password": "test123",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "nonexistent",
                "password": "wrong",
            }
        )
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]