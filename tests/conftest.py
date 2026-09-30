import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator

from services.api.app.main import app
from services.api.app.core.database import Base, get_db
from services.api.app.core.config import settings

# Синхронный драйвер для тестов
TEST_DATABASE_URL = settings.database_url.replace(
    "postgresql+asyncpg://", "postgresql://"
)
engine = create_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
TestingSessionLocal = sessionmaker(engine, expire_on_commit=False)


def override_get_db():
    with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Асинхронный клиент для HTTP-запросов, но с синхронной БД."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="function")
async def auth_token(client: AsyncClient) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "test123",
            "role": "partner"
        }
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "test123"
        }
    )
    return response.json()["access_token"]