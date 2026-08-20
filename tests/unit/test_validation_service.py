"""Tests for ValidationService - VPN config validation (F2)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from vpn_simulator.core.config import ConfigManager
from vpn_simulator.core.database import DatabaseManager
from vpn_simulator.core.events import EventBus
from vpn_simulator.domain.validation import StepStatus
from vpn_simulator.plugins.protocols.wireguard.crypto import (
    WireGuardIdentity,
    key_to_b64,
)
from vpn_simulator.services.validation import ValidationService


async def _make_service() -> tuple[ValidationService, DatabaseManager]:
    db = DatabaseManager("sqlite+aiosqlite:///:memory:")
    await db.initialize()
    service = ValidationService(MagicMock(spec=EventBus), MagicMock(spec=ConfigManager), db)
    return service, db


def _wireguard_key() -> str:
    return key_to_b64(WireGuardIdentity.generate().private_bytes)


class TestValidateWireGuard:
    @pytest.mark.asyncio
    async def test_real_handshake_and_metrics(self):
        service, db = await _make_service()
        try:
            result = await service.validate(
                "wireguard", {"port": 0, "private_key": _wireguard_key()}
            )
            names = [s.name for s in result.steps]
            assert names == [
                "syntax",
                "port",
                "auth",
                "handshake",
                "tunnel",
                "latency",
                "throughput",
            ]
            assert result.status == "pass"
            assert result.metrics["latency_ms"] >= 0.0
            assert result.metrics["throughput_mbps"] > 0.0
        finally:
            await db.close()

    @pytest.mark.asyncio
    async def test_missing_auth_fails(self):
        service, db = await _make_service()
        try:
            result = await service.validate("wireguard", {"port": 0})
            auth = next(s for s in result.steps if s.name == "auth")
            assert auth.status == StepStatus.FAIL
            assert result.status == "fail"
        finally:
            await db.close()

    @pytest.mark.asyncio
    async def test_invalid_private_key_fails(self):
        service, db = await _make_service()
        try:
            result = await service.validate("wireguard", {"private_key": "not-base64!"})
            auth = next(s for s in result.steps if s.name == "auth")
            assert auth.status == StepStatus.FAIL
        finally:
            await db.close()


class TestValidateOtherProtocols:
    @pytest.mark.asyncio
    async def test_pptp_real_handshake(self):
        service, db = await _make_service()
        try:
            result = await service.validate(
                "pptp", {"port": 0, "username": "alice", "password": "secret"}
            )
            for name in ("handshake", "tunnel", "latency"):
                step = next(s for s in result.steps if s.name == name)
                assert step.status == StepStatus.PASS
            tunnel = next(s for s in result.steps if s.name == "tunnel")
            assert "MS-CHAPv2 认证成功" in tunnel.message
            assert result.status == "pass"
        finally:
            await db.close()

    @pytest.mark.asyncio
    async def test_unsupported_protocol_raises(self):
        service, db = await _make_service()
        try:
            with pytest.raises(ValueError, match="Unsupported protocol"):
                await service.validate("bogus", {})
        finally:
            await db.close()

    @pytest.mark.asyncio
    async def test_openvpn_real_handshake(self):
        service, db = await _make_service()
        try:
            result = await service.validate(
                "openvpn", {"port": 0, "ca": "ca", "cert": "cert", "key": "key"}
            )
            for name in ("handshake", "tunnel", "latency"):
                step = next(s for s in result.steps if s.name == name)
                assert step.status == StepStatus.PASS
            assert result.status == "pass"
        finally:
            await db.close()

    @pytest.mark.asyncio
    async def test_sstp_openconnect_mschapv2(self):
        service, db = await _make_service()
        try:
            for protocol in ("sstp", "openconnect"):
                result = await service.validate(
                    protocol, {"port": 0, "username": "alice", "password": "secret"}
                )
                tunnel = next(s for s in result.steps if s.name == "tunnel")
                assert tunnel.status == StepStatus.PASS
                assert "MS-CHAPv2 认证成功" in tunnel.message
                assert result.status == "pass"
        finally:
            await db.close()


class TestBatchAndHistory:
    @pytest.mark.asyncio
    async def test_batch_validates_nine_protocols(self):
        service, db = await _make_service()
        try:
            results = await service.batch()
            assert len(results) == 9
            protocols = {r["protocol"] for r in results}
            assert protocols == {
                "pptp",
                "l2tp",
                "openvpn",
                "ipsec",
                "ikev2",
                "wireguard",
                "sstp",
                "vxlan",
                "openconnect",
            }
        finally:
            await db.close()

    @pytest.mark.asyncio
    async def test_history_persists_results(self):
        service, db = await _make_service()
        try:
            await service.validate("pptp", {"port": 0, "username": "u", "password": "p"})
            await service.validate("l2tp", {"port": 0, "secret": "s"})
            history = await service.history()
            assert len(history) == 2
            pptp_history = await service.history(protocol="pptp")
            assert len(pptp_history) == 1
            assert pptp_history[0]["protocol"] == "pptp"
        finally:
            await db.close()
