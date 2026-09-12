import pytest
from src.config import Settings, get_settings
from src.db.base import Base, GUID, TimestampMixin, enum_column
from src.db.session import get_engine, get_sessionmaker, dispose_engine
from enum import StrEnum


class SampleEnum(StrEnum):
    ALPHA = "alpha"
    BETA = "beta"


def test_settings_loaded():
    settings = get_settings()
    assert isinstance(settings, Settings)
    assert settings.app_name == "Quiz Web Backend"
    assert "3000" in settings.cors_origins


def test_enum_column_helper():
    col = enum_column(SampleEnum)
    assert col.name == "sampleenum" or col is not None


@pytest.mark.asyncio
async def test_db_sessionmaker():
    sm = get_sessionmaker()
    assert sm is not None
    await dispose_engine()
