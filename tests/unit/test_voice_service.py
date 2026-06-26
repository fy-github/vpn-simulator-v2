"""Tests for VoiceService - voice simulation service."""

from __future__ import annotations

import pytest

from vpn_simulator.services.voice import (
    CallState,
    CodecConfig,
    NetworkConditions,
    QualityMetrics,
    VoiceCall,
    VoiceCodec,
    VoiceService,
)


@pytest.fixture
def service() -> VoiceService:
    return VoiceService()


class TestVoiceServiceInit:
    def test_service_creation(self, service: VoiceService):
        assert service is not None
        assert len(service._calls) == 0
        assert service._active_calls == 0
        assert service._total_calls == 0


class TestListCodecs:
    def test_list_codecs(self, service: VoiceService):
        codecs = service.list_codecs()
        assert len(codecs) == 3
        assert any(c["id"] == "g711" for c in codecs)
        assert any(c["id"] == "g729" for c in codecs)
        assert any(c["id"] == "opus" for c in codecs)

    def test_codec_structure(self, service: VoiceService):
        codecs = service.list_codecs()
        codec = codecs[0]
        assert "id" in codec
        assert "name" in codec
        assert "description" in codec
        assert "bitrate_kbps" in codec
        assert "sample_rate_hz" in codec
        assert "frame_size_ms" in codec
        assert "packet_size_bytes" in codec
        assert "bandwidth_range" in codec


class TestStartCall:
    @pytest.mark.asyncio
    async def test_start_call_g711(self, service: VoiceService):
        result = await service.start_call(codec="g711")
        assert result["codec"] == "G.711"
        assert result["state"] == "active"
        assert "call_id" in result

    @pytest.mark.asyncio
    async def test_start_call_g729(self, service: VoiceService):
        result = await service.start_call(codec="g729")
        assert result["codec"] == "G.729"

    @pytest.mark.asyncio
    async def test_start_call_opus(self, service: VoiceService):
        result = await service.start_call(codec="opus")
        assert result["codec"] == "Opus"

    @pytest.mark.asyncio
    async def test_start_call_invalid_codec(self, service: VoiceService):
        with pytest.raises(ValueError, match="Invalid codec"):
            await service.start_call(codec="invalid")

    @pytest.mark.asyncio
    async def test_start_call_with_params(self, service: VoiceService):
        result = await service.start_call(
            codec="g711",
            caller_ip="192.168.1.100",
            callee_ip="10.0.0.50",
            latency_ms=100,
            jitter_ms=20,
            packet_loss_percent=1.0,
            bandwidth_kbps=5000,
        )
        assert result["caller_ip"] == "192.168.1.100"
        assert result["callee_ip"] == "10.0.0.50"

    @pytest.mark.asyncio
    async def test_start_call_creates_call(self, service: VoiceService):
        await service.start_call(codec="g711")
        assert len(service._calls) == 1
        assert service._active_calls == 1
        assert service._total_calls == 1

    @pytest.mark.asyncio
    async def test_start_call_default_params(self, service: VoiceService):
        result = await service.start_call()
        assert result["codec"] == "G.711"
        assert result["caller_ip"] == "192.168.1.100"
        assert result["callee_ip"] == "10.0.0.50"


class TestStopCall:
    @pytest.mark.asyncio
    async def test_stop_call(self, service: VoiceService):
        start_result = await service.start_call(codec="g711")
        call_id = start_result["call_id"]
        result = await service.stop_call(call_id)
        assert result["state"] == "completed"
        assert "duration_seconds" in result
        assert "final_metrics" in result

    @pytest.mark.asyncio
    async def test_stop_call_not_found(self, service: VoiceService):
        with pytest.raises(ValueError, match="not found"):
            await service.stop_call("nonexistent")

    @pytest.mark.asyncio
    async def test_stop_call_updates_counters(self, service: VoiceService):
        await service.start_call(codec="g711")
        calls = list(service._calls.values())
        await service.stop_call(calls[0].call_id)
        assert service._active_calls == 0

    @pytest.mark.asyncio
    async def test_stop_call_final_metrics(self, service: VoiceService):
        start_result = await service.start_call(codec="g711")
        result = await service.stop_call(start_result["call_id"])
        metrics = result["final_metrics"]
        assert "mos" in metrics
        assert "r_factor" in metrics
        assert "jitter_ms" in metrics
        assert "packet_loss_percent" in metrics


class TestGetCallStatus:
    @pytest.mark.asyncio
    async def test_get_call_status(self, service: VoiceService):
        start_result = await service.start_call(codec="g711")
        status = await service.get_call_status(start_result["call_id"])
        assert status is not None
        assert status["state"] == "active"
        assert status["codec"] == "G.711"

    @pytest.mark.asyncio
    async def test_get_call_status_not_found(self, service: VoiceService):
        status = await service.get_call_status("nonexistent")
        assert status is None

    @pytest.mark.asyncio
    async def test_get_call_status_structure(self, service: VoiceService):
        start_result = await service.start_call(codec="g711")
        status = await service.get_call_status(start_result["call_id"])
        assert "call_id" in status
        assert "codec" in status
        assert "caller_ip" in status
        assert "callee_ip" in status
        assert "state" in status
        assert "network_conditions" in status
        assert "quality_metrics" in status


class TestGetCallQuality:
    @pytest.mark.asyncio
    async def test_get_call_quality(self, service: VoiceService):
        start_result = await service.start_call(codec="g711")
        quality = await service.get_call_quality(start_result["call_id"])
        assert quality is not None
        assert "call_id" in quality
        assert "quality_metrics" in quality
        assert "quality_history" in quality

    @pytest.mark.asyncio
    async def test_get_call_quality_not_found(self, service: VoiceService):
        quality = await service.get_call_quality("nonexistent")
        assert quality is None


class TestGetStatistics:
    @pytest.mark.asyncio
    async def test_get_statistics_empty(self, service: VoiceService):
        stats = await service.get_statistics()
        assert stats["total_calls"] == 0
        assert stats["active_calls"] == 0

    @pytest.mark.asyncio
    async def test_get_statistics_with_calls(self, service: VoiceService):
        await service.start_call(codec="g711")
        await service.start_call(codec="g729")
        stats = await service.get_statistics()
        assert stats["total_calls"] == 2
        assert stats["active_calls"] == 2

    @pytest.mark.asyncio
    async def test_get_statistics_structure(self, service: VoiceService):
        await service.start_call(codec="g711")
        stats = await service.get_statistics()
        assert "total_calls" in stats
        assert "active_calls" in stats
        assert "active_call_list" in stats
        assert "supported_codecs" in stats


class TestUpdateNetworkConditions:
    @pytest.mark.asyncio
    async def test_update_network_conditions(self, service: VoiceService):
        start_result = await service.start_call(codec="g711")
        result = service.update_network_conditions(
            start_result["call_id"],
            latency_ms=200,
            jitter_ms=50,
            packet_loss_percent=5.0,
        )
        assert result is not None
        assert result["network_conditions"]["latency_ms"] == 200

    @pytest.mark.asyncio
    async def test_update_network_conditions_not_found(self, service: VoiceService):
        with pytest.raises(ValueError, match="not found"):
            service.update_network_conditions("nonexistent", latency_ms=100)


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_multiple_calls(self, service: VoiceService):
        await service.start_call(codec="g711")
        await service.start_call(codec="g729")
        await service.start_call(codec="opus")
        assert service._active_calls == 3
        assert service._total_calls == 3

    @pytest.mark.asyncio
    async def test_call_state_transitions(self, service: VoiceService):
        result = await service.start_call(codec="g711")
        assert result["state"] == "active"
        
        stop_result = await service.stop_call(result["call_id"])
        assert stop_result["state"] == "completed"

    @pytest.mark.asyncio
    async def test_codec_configs_valid(self, service: VoiceService):
        for codec in [VoiceCodec.G711, VoiceCodec.G729, VoiceCodec.OPUS]:
            from vpn_simulator.services.voice import CODEC_CONFIGS
            config = CODEC_CONFIGS[codec]
            assert config.bitrate_kbps > 0
            assert config.sample_rate_hz > 0
            assert config.frame_size_ms > 0
            assert config.packet_size_bytes > 0

    @pytest.mark.asyncio
    async def test_quality_metrics_structure(self, service: VoiceService):
        start_result = await service.start_call(codec="g711")
        status = await service.get_call_status(start_result["call_id"])
        metrics = status["quality_metrics"]
        assert "mos" in metrics
        assert "r_factor" in metrics
        assert "jitter_ms" in metrics
        assert "packet_loss_percent" in metrics
        assert "latency_ms" in metrics
        assert "packets_sent" in metrics
        assert "packets_received" in metrics
        assert "packets_lost" in metrics
        assert "bytes_sent" in metrics
        assert "bytes_received" in metrics
