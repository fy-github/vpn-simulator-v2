import logging

"""Configuration management routes for VPN Simulator v2."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config")


class ServerConfig(BaseModel):
    """Server configuration."""

    host: str = Field("0.0.0.0", description="Server host")
    port: int = Field(8080, description="Server port")


class Config(BaseModel):
    """Application configuration."""

    server: ServerConfig = Field(default_factory=ServerConfig, description="Server config")
    protocols: dict[str, Any] = Field(default_factory=dict, description="Protocol configs")
    faults: dict[str, Any] = Field(default_factory=dict, description="Fault configs")
    logging: dict[str, Any] = Field(default_factory=dict, description="Logging config")


@router.get(
    "",
    response_model=Config,
    summary="Get configuration",
    description="Retrieve the current application configuration.",
)
async def get_config() -> dict[str, Any]:
    """Get current configuration."""
    return {
        "server": {"host": "0.0.0.0", "port": 8080},
        "protocols": {},
        "faults": {},
        "logging": {"level": "INFO", "format": "json"},
    }


@router.put(
    "",
    response_model=Config,
    summary="Update configuration",
    description="Update the application configuration.",
)
async def update_config(config: Config) -> dict[str, Any]:
    """Update configuration."""
    return config.model_dump()
