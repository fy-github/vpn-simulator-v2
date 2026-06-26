"""Tests for TutorialService - tutorial guidance service."""

from __future__ import annotations

import pytest
from pathlib import Path

from vpn_simulator.services.tutorial import TutorialService


@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Path:
    config_dir = tmp_path / "tutorials"
    config_dir.mkdir()
    
    tutorial_data = {
        "name": "PPTP Basics",
        "protocol": "pptp",
        "description": "Learn PPTP protocol basics",
        "difficulty": "beginner",
        "estimated_time": 15,
        "steps": [
            {
                "title": "Step 1: Connection Initiation",
                "description": "Client sends SCCRQ to server",
                "packet_info": "SCCRQ: SCCRQ message",
                "rfc_reference": "RFC 2637 Section 3.1",
                "expected_state": "WAIT_SCCRQ",
                "hint": "The client initiates the connection",
            },
            {
                "title": "Step 2: Server Response",
                "description": "Server responds with SCCRP",
                "packet_info": "SCCRP: SCCRP message",
                "rfc_reference": "RFC 2637 Section 3.2",
                "expected_state": "SCCRP_SENT",
                "hint": "The server acknowledges",
            },
            {
                "title": "Step 3: GRE Tunnel",
                "description": "GRE tunnel established",
                "packet_info": "GRE: GRE encapsulated data",
                "rfc_reference": "RFC 2637 Section 4",
                "expected_state": "GRE_ESTABLISHED",
                "hint": "GRE tunnel is now active",
            },
        ],
    }
    
    import yaml
    (config_dir / "pptp_basics.yaml").write_text(yaml.dump(tutorial_data, allow_unicode=True))
    
    return config_dir


@pytest.fixture
def service(temp_config_dir: Path) -> TutorialService:
    return TutorialService(config_path=str(temp_config_dir))


@pytest.fixture
def empty_service(tmp_path: Path) -> TutorialService:
    return TutorialService(config_path=str(tmp_path / "nonexistent"))


class TestTutorialServiceInit:
    def test_service_creation_with_config(self, service: TutorialService):
        assert service is not None
        assert len(service._tutorials) == 1
        assert "pptp_basics" in service._tutorials

    def test_service_creation_without_config(self, empty_service: TutorialService):
        assert empty_service is not None
        assert len(empty_service._tutorials) == 0


class TestListTutorials:
    @pytest.mark.asyncio
    async def test_list_tutorials(self, service: TutorialService):
        tutorials = await service.list_tutorials()
        assert len(tutorials) == 1
        assert tutorials[0]["id"] == "pptp_basics"
        assert tutorials[0]["name"] == "PPTP Basics"
        assert tutorials[0]["protocol"] == "pptp"
        assert tutorials[0]["total_steps"] == 3

    @pytest.mark.asyncio
    async def test_list_tutorials_empty(self, empty_service: TutorialService):
        tutorials = await empty_service.list_tutorials()
        assert len(tutorials) == 0


class TestGetTutorial:
    @pytest.mark.asyncio
    async def test_get_tutorial(self, service: TutorialService):
        tutorial = await service.get_tutorial("pptp_basics")
        assert tutorial is not None
        assert tutorial["id"] == "pptp_basics"
        assert tutorial["name"] == "PPTP Basics"
        assert len(tutorial["steps"]) == 3

    @pytest.mark.asyncio
    async def test_get_tutorial_not_found(self, service: TutorialService):
        tutorial = await service.get_tutorial("nonexistent")
        assert tutorial is None

    @pytest.mark.asyncio
    async def test_get_tutorial_step_structure(self, service: TutorialService):
        tutorial = await service.get_tutorial("pptp_basics")
        step = tutorial["steps"][0]
        assert "title" in step
        assert "description" in step
        assert "packet_info" in step
        assert "rfc_reference" in step
        assert "expected_state" in step
        assert "hint" in step


class TestStartTutorial:
    @pytest.mark.asyncio
    async def test_start_tutorial(self, service: TutorialService):
        result = await service.start_tutorial("pptp_basics")
        assert result["tutorial_id"] == "pptp_basics"
        assert result["current_step"] == 0
        assert result["total_steps"] == 3
        assert result["is_completed"] is False
        assert result["current_step_info"] is not None
        assert result["current_step_info"]["title"] == "Step 1: Connection Initiation"

    @pytest.mark.asyncio
    async def test_start_tutorial_not_found(self, service: TutorialService):
        with pytest.raises(ValueError, match="not found"):
            await service.start_tutorial("nonexistent")

    @pytest.mark.asyncio
    async def test_start_tutorial_creates_session(self, service: TutorialService):
        await service.start_tutorial("pptp_basics")
        assert "pptp_basics" in service._sessions

    @pytest.mark.asyncio
    async def test_start_tutorial_resets_completed(self, service: TutorialService):
        await service.start_tutorial("pptp_basics")
        session = service._sessions["pptp_basics"]
        session.complete()
        
        result = await service.start_tutorial("pptp_basics")
        assert result["is_completed"] is False
        assert result["current_step"] == 0


class TestNextStep:
    @pytest.mark.asyncio
    async def test_next_step(self, service: TutorialService):
        await service.start_tutorial("pptp_basics")
        result = await service.next_step("pptp_basics")
        assert result["current_step"] == 1
        assert result["is_completed"] is False
        assert result["current_step_info"]["title"] == "Step 2: Server Response"

    @pytest.mark.asyncio
    async def test_next_step_to_completion(self, service: TutorialService):
        await service.start_tutorial("pptp_basics")
        await service.next_step("pptp_basics")
        await service.next_step("pptp_basics")
        result = await service.next_step("pptp_basics")
        assert result["is_completed"] is True

    @pytest.mark.asyncio
    async def test_next_step_already_completed(self, service: TutorialService):
        await service.start_tutorial("pptp_basics")
        await service.next_step("pptp_basics")
        await service.next_step("pptp_basics")
        await service.next_step("pptp_basics")
        
        result = await service.next_step("pptp_basics")
        assert result["is_completed"] is True
        assert "completed" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_next_step_tutorial_not_found(self, service: TutorialService):
        with pytest.raises(ValueError, match="not found"):
            await service.next_step("nonexistent")

    @pytest.mark.asyncio
    async def test_next_step_session_not_started(self, service: TutorialService):
        with pytest.raises(ValueError, match="not started"):
            await service.next_step("pptp_basics")


class TestPrevStep:
    @pytest.mark.asyncio
    async def test_prev_step(self, service: TutorialService):
        await service.start_tutorial("pptp_basics")
        await service.next_step("pptp_basics")
        result = await service.prev_step("pptp_basics")
        assert result["current_step"] == 0

    @pytest.mark.asyncio
    async def test_prev_step_at_first(self, service: TutorialService):
        await service.start_tutorial("pptp_basics")
        result = await service.prev_step("pptp_basics")
        assert result["current_step"] == 0
        assert "first step" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_prev_step_tutorial_not_found(self, service: TutorialService):
        with pytest.raises(ValueError, match="not found"):
            await service.prev_step("nonexistent")

    @pytest.mark.asyncio
    async def test_prev_step_session_not_started(self, service: TutorialService):
        with pytest.raises(ValueError, match="not started"):
            await service.prev_step("pptp_basics")


class TestResetTutorial:
    @pytest.mark.asyncio
    async def test_reset_tutorial(self, service: TutorialService):
        await service.start_tutorial("pptp_basics")
        await service.next_step("pptp_basics")
        await service.next_step("pptp_basics")
        
        result = await service.reset_tutorial("pptp_basics")
        assert result["current_step"] == 0
        assert result["is_completed"] is False

    @pytest.mark.asyncio
    async def test_reset_tutorial_tutorial_not_found(self, service: TutorialService):
        with pytest.raises(ValueError, match="not found"):
            await service.reset_tutorial("nonexistent")

    @pytest.mark.asyncio
    async def test_reset_tutorial_session_not_started(self, service: TutorialService):
        with pytest.raises(ValueError, match="not started"):
            await service.reset_tutorial("pptp_basics")


class TestGetTutorialSession:
    @pytest.mark.asyncio
    async def test_get_tutorial_session(self, service: TutorialService):
        await service.start_tutorial("pptp_basics")
        session = await service.get_tutorial_session("pptp_basics")
        assert session is not None
        assert session["tutorial_id"] == "pptp_basics"
        assert session["current_step"] == 0
        assert session["total_steps"] == 3
        assert session["is_completed"] is False

    @pytest.mark.asyncio
    async def test_get_tutorial_session_not_found(self, service: TutorialService):
        session = await service.get_tutorial_session("nonexistent")
        assert session is None

    @pytest.mark.asyncio
    async def test_get_tutorial_session_after_steps(self, service: TutorialService):
        await service.start_tutorial("pptp_basics")
        await service.next_step("pptp_basics")
        
        session = await service.get_tutorial_session("pptp_basics")
        assert session["current_step"] == 1


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_multiple_tutorials(self, temp_config_dir: Path):
        tutorial2 = {
            "name": "L2TP Basics",
            "protocol": "l2tp",
            "description": "Learn L2TP",
            "difficulty": "intermediate",
            "estimated_time": 20,
            "steps": [
                {"title": "Step 1", "description": "Init", "packet_info": "", "rfc_reference": "", "expected_state": "", "hint": ""},
            ],
        }
        import yaml
        (temp_config_dir / "l2tp_basics.yaml").write_text(yaml.dump(tutorial2))
        
        service = TutorialService(config_path=str(temp_config_dir))
        tutorials = await service.list_tutorials()
        assert len(tutorials) == 2

    @pytest.mark.asyncio
    async def test_full_workflow(self, service: TutorialService):
        await service.start_tutorial("pptp_basics")
        
        result = await service.next_step("pptp_basics")
        assert result["current_step"] == 1
        
        result = await service.next_step("pptp_basics")
        assert result["current_step"] == 2
        
        result = await service.next_step("pptp_basics")
        assert result["is_completed"] is True
        
        await service.reset_tutorial("pptp_basics")
        session = await service.get_tutorial_session("pptp_basics")
        assert session["current_step"] == 0
        assert session["is_completed"] is False
