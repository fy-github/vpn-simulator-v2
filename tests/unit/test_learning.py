"""Tests for LearningService - learning resources service."""

from __future__ import annotations

import pytest
import pytest_asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from vpn_simulator.services.learning import LearningService


@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Path:
    config_dir = tmp_path / "learning"
    config_dir.mkdir()
    
    rfc_data = {
        "protocols": {
            "pptp": {
                "name": "PPTP",
                "full_name": "Point-to-Point Tunneling Protocol",
                "rfcs": [
                    {
                        "number": "RFC 2637",
                        "title": "Point-to-Point Tunneling Protocol",
                        "url": "https://tools.ietf.org/html/rfc2637",
                        "description": "PPTP specification",
                        "published": "1999-07",
                        "status": "Informational",
                    }
                ],
                "references": [
                    {
                        "title": "PPTP Wikipedia",
                        "url": "https://en.wikipedia.org/wiki/Point-to-Point_Tunneling_Protocol",
                        "description": "Wikipedia article on PPTP",
                    }
                ],
            },
            "l2tp": {
                "name": "L2TP",
                "full_name": "Layer 2 Tunneling Protocol",
                "rfcs": [
                    {
                        "number": "RFC 2661",
                        "title": "Layer Two Tunneling Protocol",
                        "url": "https://tools.ietf.org/html/rfc2661",
                        "description": "L2TP specification",
                        "published": "1999-08",
                        "status": "Proposed Standard",
                    }
                ],
                "references": [],
            },
        }
    }
    
    faq_data = {
        "categories": [
            {
                "id": "general",
                "name": "General",
                "icon": "help-circle",
                "questions": [
                    {
                        "id": "what_is_vpn",
                        "question": "What is a VPN?",
                        "answer": "A VPN is a virtual private network.",
                        "tags": ["basics", "introduction"],
                    },
                    {
                        "id": "vpn_protocols",
                        "question": "What are VPN protocols?",
                        "answer": "VPN protocols are...",
                        "tags": ["protocols", "basics"],
                    },
                ],
            },
            {
                "id": "security",
                "name": "Security",
                "icon": "shield",
                "questions": [
                    {
                        "id": "is_vpn_safe",
                        "question": "Is VPN safe?",
                        "answer": "Yes, when configured properly.",
                        "tags": ["security", "safety"],
                    },
                ],
            },
        ]
    }
    
    paths_data = {
        "paths": [
            {
                "id": "beginner",
                "name": "Beginner Path",
                "description": "For beginners",
                "icon": "target",
                "difficulty": "beginner",
                "estimated_hours": 8,
                "target_audience": "Network students",
                "prerequisites": [],
                "protocols": [
                    {"protocol": "pptp", "order": 1, "title": "PPTP Basics"},
                    {"protocol": "l2tp", "order": 2, "title": "L2TP Basics"},
                ],
            },
            {
                "id": "advanced",
                "name": "Advanced Path",
                "description": "For advanced users",
                "icon": "lock",
                "difficulty": "advanced",
                "estimated_hours": 15,
                "target_audience": "Security researchers",
                "prerequisites": ["Network basics", "Cryptography"],
                "protocols": [
                    {"protocol": "ipsec", "order": 1, "title": "IPSec Deep Dive"},
                ],
            },
        ],
        "milestones": [
            {"path_id": "beginner", "title": "First Connection", "description": "Complete first VPN connection"},
            {"path_id": "advanced", "title": "Security Expert", "description": "Master IPSec"},
        ],
    }
    
    import yaml
    (config_dir / "rfc_references.yaml").write_text(yaml.dump(rfc_data, allow_unicode=True))
    (config_dir / "faq.yaml").write_text(yaml.dump(faq_data, allow_unicode=True))
    (config_dir / "learning_paths.yaml").write_text(yaml.dump(paths_data, allow_unicode=True))
    
    return config_dir


@pytest.fixture
def service(temp_config_dir: Path) -> LearningService:
    return LearningService(config_path=str(temp_config_dir))


@pytest.fixture
def empty_service(tmp_path: Path) -> LearningService:
    return LearningService(config_path=str(tmp_path / "nonexistent"))


class TestLearningServiceInit:
    def test_service_creation_with_config(self, service: LearningService):
        assert service is not None
        assert len(service._rfc_references) == 2
        assert len(service._faq.get("categories", [])) == 2
        assert len(service._learning_paths) == 2

    def test_service_creation_without_config(self, empty_service: LearningService):
        assert empty_service is not None
        assert len(empty_service._rfc_references) == 0
        assert len(empty_service._faq) == 0
        assert len(empty_service._learning_paths) == 0


class TestRFCReferences:
    @pytest.mark.asyncio
    async def test_list_all_rfc_references(self, service: LearningService):
        refs = await service.list_rfc_references()
        assert len(refs) == 3
        assert any(r["protocol"] == "pptp" for r in refs)
        assert any(r["protocol"] == "l2tp" for r in refs)

    @pytest.mark.asyncio
    async def test_list_rfc_references_by_protocol(self, service: LearningService):
        refs = await service.list_rfc_references(protocol="pptp")
        assert len(refs) == 2
        assert all(r["protocol"] == "pptp" for r in refs)

    @pytest.mark.asyncio
    async def test_list_rfc_references_unknown_protocol(self, service: LearningService):
        refs = await service.list_rfc_references(protocol="unknown")
        assert len(refs) == 0

    @pytest.mark.asyncio
    async def test_get_protocol_rfc_references(self, service: LearningService):
        result = await service.get_protocol_rfc_references("pptp")
        assert result["protocol"] == "pptp"
        assert result["name"] == "PPTP"
        assert len(result["rfcs"]) == 1
        assert len(result["references"]) == 1

    @pytest.mark.asyncio
    async def test_get_protocol_rfc_references_not_found(self, service: LearningService):
        with pytest.raises(ValueError, match="not found"):
            await service.get_protocol_rfc_references("unknown")

    @pytest.mark.asyncio
    async def test_rfc_reference_structure(self, service: LearningService):
        refs = await service.list_rfc_references(protocol="pptp")
        rfc_ref = refs[0]
        assert rfc_ref["type"] == "rfc"
        assert rfc_ref["number"] == "RFC 2637"
        assert rfc_ref["protocol_name"] == "PPTP"

    @pytest.mark.asyncio
    async def test_reference_structure(self, service: LearningService):
        refs = await service.list_rfc_references(protocol="pptp")
        ref = [r for r in refs if r["type"] == "reference"][0]
        assert ref["type"] == "reference"
        assert ref["number"] == ""


class TestFAQ:
    @pytest.mark.asyncio
    async def test_list_all_faq(self, service: LearningService):
        faq = await service.list_faq()
        assert len(faq) == 3

    @pytest.mark.asyncio
    async def test_list_faq_by_category(self, service: LearningService):
        faq = await service.list_faq(category="general")
        assert len(faq) == 2
        assert all(f["category_id"] == "general" for f in faq)

    @pytest.mark.asyncio
    async def test_list_faq_unknown_category(self, service: LearningService):
        faq = await service.list_faq(category="unknown")
        assert len(faq) == 0

    @pytest.mark.asyncio
    async def test_get_faq_categories(self, service: LearningService):
        categories = await service.get_faq_categories()
        assert len(categories) == 2
        assert categories[0]["id"] == "general"
        assert categories[0]["question_count"] == 2

    @pytest.mark.asyncio
    async def test_get_faq_item(self, service: LearningService):
        item = await service.get_faq_item("what_is_vpn")
        assert item is not None
        assert item["id"] == "what_is_vpn"
        assert item["question"] == "What is a VPN?"

    @pytest.mark.asyncio
    async def test_get_faq_item_not_found(self, service: LearningService):
        item = await service.get_faq_item("nonexistent")
        assert item is None

    @pytest.mark.asyncio
    async def test_faq_structure(self, service: LearningService):
        faq = await service.list_faq()
        item = faq[0]
        assert "category_id" in item
        assert "category_name" in item
        assert "id" in item
        assert "question" in item
        assert "answer" in item
        assert "tags" in item


class TestLearningPaths:
    @pytest.mark.asyncio
    async def test_list_learning_paths(self, service: LearningService):
        paths = await service.list_learning_paths()
        assert len(paths) == 2
        assert any(p["id"] == "beginner" for p in paths)
        assert any(p["id"] == "advanced" for p in paths)

    @pytest.mark.asyncio
    async def test_get_learning_path(self, service: LearningService):
        path = await service.get_learning_path("beginner")
        assert path is not None
        assert path["id"] == "beginner"
        assert path["name"] == "Beginner Path"
        assert path["difficulty"] == "beginner"
        assert len(path["protocols"]) == 2

    @pytest.mark.asyncio
    async def test_get_learning_path_not_found(self, service: LearningService):
        path = await service.get_learning_path("nonexistent")
        assert path is None

    @pytest.mark.asyncio
    async def test_get_learning_path_milestones(self, service: LearningService):
        milestones = await service.get_learning_path_milestones("beginner")
        assert len(milestones) == 1
        assert milestones[0]["title"] == "First Connection"

    @pytest.mark.asyncio
    async def test_learning_path_structure(self, service: LearningService):
        paths = await service.list_learning_paths()
        path = paths[0]
        assert "id" in path
        assert "name" in path
        assert "description" in path
        assert "difficulty" in path
        assert "estimated_hours" in path
        assert "protocol_count" in path


class TestSearchResources:
    @pytest.mark.asyncio
    async def test_search_rfc(self, service: LearningService):
        result = await service.search_resources("PPTP")
        assert len(result["rfc_references"]) > 0

    @pytest.mark.asyncio
    async def test_search_faq(self, service: LearningService):
        result = await service.search_resources("VPN")
        assert len(result["faq"]) > 0

    @pytest.mark.asyncio
    async def test_search_learning_paths(self, service: LearningService):
        result = await service.search_resources("Beginner")
        assert len(result["learning_paths"]) > 0

    @pytest.mark.asyncio
    async def test_search_no_results(self, service: LearningService):
        result = await service.search_resources("xyznonexistent")
        assert len(result["rfc_references"]) == 0
        assert len(result["faq"]) == 0
        assert len(result["learning_paths"]) == 0

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self, service: LearningService):
        result = await service.search_resources("pptp")
        assert len(result["rfc_references"]) > 0

    @pytest.mark.asyncio
    async def test_search_structure(self, service: LearningService):
        result = await service.search_resources("VPN")
        assert "rfc_references" in result
        assert "faq" in result
        assert "learning_paths" in result


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_empty_service_list_rfc(self, empty_service: LearningService):
        refs = await empty_service.list_rfc_references()
        assert len(refs) == 0

    @pytest.mark.asyncio
    async def test_empty_service_list_faq(self, empty_service: LearningService):
        faq = await empty_service.list_faq()
        assert len(faq) == 0

    @pytest.mark.asyncio
    async def test_empty_service_list_paths(self, empty_service: LearningService):
        paths = await empty_service.list_learning_paths()
        assert len(paths) == 0

    @pytest.mark.asyncio
    async def test_empty_service_search(self, empty_service: LearningService):
        result = await empty_service.search_resources("test")
        assert len(result["rfc_references"]) == 0
        assert len(result["faq"]) == 0
        assert len(result["learning_paths"]) == 0
