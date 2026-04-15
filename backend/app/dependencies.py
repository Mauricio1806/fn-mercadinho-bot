"""Injeção de dependências do FastAPI."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import BusinessConfig, Settings, get_business_config, get_settings
from app.database.session import get_db


def get_settings_dep() -> Settings:
    return get_settings()


def get_business_config_dep() -> BusinessConfig:
    return get_business_config()
