"""FastAPI application entry point for VPN Simulator v2."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vpn_simulator.logging_setup import configure_logging

# 必须在 import 绑定 structlog logger 的模块（middleware / routers）之前调用，
# 因为 structlog 会缓存每个名字的首个 logger。
configure_logging()

from vpn_simulator.api.middleware.auth import AuthMiddleware  # noqa: E402
from vpn_simulator.api.middleware.logging import RequestLoggingMiddleware  # noqa: E402
from vpn_simulator.api.routers import (  # noqa: E402
    attacks,
    benchmark,
    comparison,
    config,
    connections,
    dhcp,
    dpi,
    faults,
    impairment,
    iot,
    learning,
    logs,
    metrics,
    obfuscation,
    packets,
    pcap,
    protocols,
    scenarios,
    snmp,
    stats,
    topology,
    traffic,
    tutorials,
    validation,
    vendor_cli,
    voice,
)
from vpn_simulator.api.websocket import websocket_endpoint, ws_manager  # noqa: E402

logger = structlog.get_logger(__name__)

# 可选 API Key：设置 VPN_SIM_API_KEY 环境变量后，除公开路径外均需携带
# X-API-Key 请求头。未设置时保持免认证（本地教学工具默认行为）。
_API_KEY = os.getenv("VPN_SIM_API_KEY")


async def _load_plugins() -> None:
    """Load all plugins from the plugins directory."""
    from vpn_simulator.core.config import ConfigManager
    from vpn_simulator.core.events import EventBus
    from vpn_simulator.plugins.context import PluginContext
    from vpn_simulator.plugins.loader import PluginLoader

    event_bus = EventBus()
    config_manager = ConfigManager()
    context = PluginContext(event_bus=event_bus, config=config_manager)
    loader = PluginLoader(context)

    # 插件实现（protocols / faults / attacks / exporters）已合并进
    # vpn_simulator.plugins 包内，因此路径是确定的。
    plugins_dir = Path(__file__).parent.parent / "plugins"
    if not plugins_dir.is_dir():
        logger.warning("Plugins directory not found, skipping plugin loading")
        return

    # Load protocol plugins
    protocols_dir = plugins_dir / "protocols"
    if protocols_dir.exists():
        loaded = await loader.load_directory(protocols_dir)
        logger.info(f"Loaded {len(loaded)} protocol plugins: {loaded}")

    # Load fault plugins
    faults_dir = plugins_dir / "faults"
    if faults_dir.exists():
        loaded = await loader.load_directory(faults_dir)
        logger.info(f"Loaded {len(loaded)} fault plugins: {loaded}")

    # Load attack plugins
    attacks_dir = plugins_dir / "attacks"
    if attacks_dir.exists():
        loaded = await loader.load_directory(attacks_dir)
        logger.info(f"Loaded {len(loaded)} attack plugins: {loaded}")

    # Load exporter plugins
    exporters_dir = plugins_dir / "exporters"
    if exporters_dir.exists():
        loaded = await loader.load_directory(exporters_dir)
        logger.info(f"Loaded {len(loaded)} exporter plugins: {loaded}")

    # Initialize all loaded plugins
    initialized = await loader.initialize_all()
    logger.info(f"Initialized {len(initialized)} plugins: {initialized}")


async def _restore_state() -> None:
    """从数据库恢复协议/连接/故障/攻击的持久化状态。

    必须在 _load_plugins()（注册插件并初始化状态机）和 initialize_database()
    之后调用，使各服务的领域状态与数据库一致。
    """
    from vpn_simulator.api.routers.attacks import get_attack_service
    from vpn_simulator.api.routers.connections import get_connection_service
    from vpn_simulator.api.routers.faults import get_fault_service
    from vpn_simulator.api.routers.impairment import get_impairment_service
    from vpn_simulator.api.routers.protocols import get_protocol_service

    await get_protocol_service().restore_protocols()
    await get_connection_service().restore_connections()
    await get_fault_service().restore_faults()
    await get_attack_service().restore_attacks()
    await get_impairment_service().restore_impairments()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown."""
    from vpn_simulator.core.database import close_database, initialize_database

    await _load_plugins()
    await initialize_database()
    await _restore_state()
    yield
    await ws_manager.disconnect_all()
    await close_database()


app = FastAPI(
    title="VPN Simulator API",
    version="2.0.0",
    description="VPN Simulator REST API for protocol simulation, fault injection, and attack testing.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    # 通配符 origin 与 allow_credentials=True 组合在浏览器端无效，故关闭凭据。
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(AuthMiddleware, api_key=_API_KEY)

app.include_router(protocols.router, prefix="/api/v1", tags=["protocols"])
app.include_router(connections.router, prefix="/api/v1", tags=["connections"])
app.include_router(faults.router, prefix="/api/v1", tags=["faults"])
app.include_router(impairment.router, prefix="/api/v1", tags=["impairments"])
app.include_router(attacks.router, prefix="/api/v1", tags=["attacks"])
app.include_router(benchmark.router, prefix="/api/v1", tags=["benchmark"])
app.include_router(topology.router, prefix="/api/v1", tags=["topology"])
app.include_router(logs.router, prefix="/api/v1", tags=["logs"])
app.include_router(stats.router, prefix="/api/v1", tags=["stats"])
app.include_router(config.router, prefix="/api/v1", tags=["config"])
app.include_router(comparison.router, prefix="/api/v1", tags=["comparison"])
app.include_router(tutorials.router, prefix="/api/v1", tags=["tutorials"])
app.include_router(learning.router, prefix="/api/v1", tags=["learning"])
app.include_router(packets.router, prefix="/api/v1", tags=["packets"])
app.include_router(pcap.router, prefix="/api/v1", tags=["pcap"])
app.include_router(scenarios.router, prefix="/api/v1", tags=["scenarios"])
app.include_router(snmp.router, prefix="/api/v1", tags=["snmp"])
app.include_router(metrics.router, prefix="/api/v1", tags=["metrics"])
app.include_router(traffic.router, prefix="/api/v1", tags=["traffic"])
app.include_router(iot.router, prefix="/api/v1", tags=["iot"])
app.include_router(dpi.router, prefix="/api/v1", tags=["dpi"])
app.include_router(obfuscation.router, prefix="/api/v1", tags=["obfuscation"])
app.include_router(voice.router, prefix="/api/v1", tags=["voice"])
app.include_router(validation.router, prefix="/api/v1", tags=["validation"])
app.include_router(vendor_cli.router, prefix="/api/v1", tags=["vendor-cli"])
app.include_router(dhcp.router, prefix="/api/v1", tags=["dhcp"])


@app.get("/health", summary="Health check", response_model=dict)
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "version": "2.0.0"}


@app.websocket("/ws")
async def ws(websocket: object, channel: str = "default") -> None:
    """WebSocket endpoint for real-time event streaming."""
    await websocket_endpoint(websocket, channel)  # type: ignore[arg-type]
