import pytest
from httpx import AsyncClient


class TestAuth:
    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        response = await client.get("/")
        print(f"Root response: {response.status_code}")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "password123",
                "role": "partner"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert data["role"] == "partner"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={
                "username": "duplicate",
                "email": "dup1@example.com",
                "password": "password123"
            }
        )
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "duplicate",
                "email": "dup2@example.com",
                "password": "password123"
            }
        )
        assert response.status_code == 400
        assert "Username duplicate already taken" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={
                "username": "loginuser",
                "email": "login@example.com",
                "password": "test123"
            }
        )
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "loginuser",
                "password": "test123"
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
                "password": "wrong"
            }
        )
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]