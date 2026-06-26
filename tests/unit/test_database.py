"""Tests for DatabaseManager - database initialization and lifecycle."""

from __future__ import annotations

import pytest
import pytest_asyncio

from vpn_simulator.core.database import DatabaseManager


@pytest_asyncio.fixture
async def db_manager(tmp_path):
    db_path = tmp_path / "test.db"
    manager = DatabaseManager(database_url=f"sqlite+aiosqlite:///{db_path}")
    await manager.initialize()
    yield manager
    await manager.close()


class TestDatabaseManagerInit:
    def test_default_url(self):
        manager = DatabaseManager()
        assert "sqlite" in manager.database_url

    def test_custom_url(self):
        manager = DatabaseManager(database_url="sqlite+aiosqlite:///test.db")
        assert manager.database_url == "sqlite+aiosqlite:///test.db"


class TestInitialize:
    @pytest.mark.asyncio
    async def test_initialize_creates_engine(self, db_manager):
        assert db_manager._engine is not None
        assert db_manager._session_factory is not None

    @pytest.mark.asyncio
    async def test_engine_property(self, db_manager):
        engine = db_manager.engine
        assert engine is not None

    @pytest.mark.asyncio
    async def test_engine_before_init_raises(self):
        manager = DatabaseManager()
        with pytest.raises(RuntimeError, match="not initialized"):
            _ = manager.engine


class TestSession:
    @pytest.mark.asyncio
    async def test_session_context_manager(self, db_manager):
        async with db_manager.session() as session:
            assert session is not None

    @pytest.mark.asyncio
    async def test_session_before_init_raises(self):
        manager = DatabaseManager()
        with pytest.raises(RuntimeError, match="not initialized"):
            async with manager.session():
                pass


class TestClose:
    @pytest.mark.asyncio
    async def test_close_disposes_engine(self):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        manager = DatabaseManager(database_url=f"sqlite+aiosqlite:///{db_path}")
        await manager.initialize()
        assert manager._engine is not None
        await manager.close()
        assert manager._engine is None
        assert manager._session_factory is None

    @pytest.mark.asyncio
    async def test_close_without_init(self):
        manager = DatabaseManager()
        await manager.close()


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_success(self, db_manager):
        result = await db_manager.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_before_init(self):
        manager = DatabaseManager()
        result = await manager.health_check()
        assert result is False
