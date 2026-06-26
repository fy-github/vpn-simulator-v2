"""混淆测试服务单元测试。"""

import pytest
from src.vpn_simulator.services.obfuscation import (
    ObfuscationService,
    ObfuscationTechnique,
    DetectionDifficulty,
    obfuscation_service,
)


class TestObfuscationService:
    """混淆测试服务测试类。"""

    def setup_method(self):
        """测试前准备。"""
        self.service = ObfuscationService()

    def test_get_supported_techniques(self):
        """测试获取支持的混淆技术。"""
        techniques = self.service.get_supported_techniques()
        assert len(techniques) == 5
        technique_names = [t["technique"] for t in techniques]
        assert "obfs4" in technique_names
        assert "shadowsocks" in technique_names
        assert "udp2raw" in technique_names
        assert "meek" in technique_names
        assert "snowflake" in technique_names

    def test_technique_info_structure(self):
        """测试技术信息结构。"""
        techniques = self.service.get_supported_techniques()
        for tech in techniques:
            assert "name" in tech
            assert "technique" in tech
            assert "description" in tech
            assert "transport_protocol" in tech
            assert "default_port" in tech
            assert "encryption" in tech
            assert "resistance_level" in tech
            assert "use_cases" in tech

    def test_run_test_obfs4(self):
        """测试运行 obfs4 混淆测试。"""
        result = self.service.run_test("obfs4")
        assert result["technique"] == "obfs4"
        assert 0 <= result["detection_rate"] <= 1
        assert 0 <= result["false_positive_rate"] <= 1
        assert 0 <= result["detection_score"] <= 100
        assert result["detection_difficulty"] in [d.value for d in DetectionDifficulty]
        assert result["packets_analyzed"] == 1000

    def test_run_test_all_techniques(self):
        """测试运行所有混淆技术测试。"""
        for tech in ObfuscationTechnique:
            result = self.service.run_test(tech.value)
            assert result["technique"] == tech.value
            assert "id" in result
            assert "timestamp" in result
            assert "traffic_features" in result
            assert "shannon_entropy" in result

    def test_run_test_invalid_technique(self):
        """测试运行无效混淆技术测试。"""
        with pytest.raises(ValueError) as exc_info:
            self.service.run_test("invalid_technique")
        assert "不支持的混淆技术" in str(exc_info.value)

    def test_traffic_features_structure(self):
        """测试流量特征结构。"""
        result = self.service.run_test("obfs4")
        features = result["traffic_features"]
        assert "avg_packet_size" in features
        assert "packet_size_std" in features
        assert "avg_interval_ms" in features
        assert "interval_std_ms" in features
        assert "burst_ratio" in features
        assert "protocol_distribution" in features
        assert "port_distribution" in features

    def test_shannon_entropy_structure(self):
        """测试 Shannon 熵结构。"""
        result = self.service.run_test("obfs4")
        entropy = result["shannon_entropy"]
        assert "payload_entropy" in entropy
        assert "header_entropy" in entropy
        assert "overall_entropy" in entropy
        assert "randomness_score" in entropy
        assert 0 <= entropy["randomness_score"] <= 1

    def test_get_results(self):
        """测试获取测试结果。"""
        self.service.run_test("obfs4")
        self.service.run_test("shadowsocks")
        results = self.service.get_results()
        assert len(results) == 2

    def test_get_results_with_limit(self):
        """测试获取测试结果（带限制）。"""
        for _ in range(5):
            self.service.run_test("obfs4")
        results = self.service.get_results(limit=3)
        assert len(results) == 3

    def test_get_comparison(self):
        """测试获取对比结果。"""
        self.service.run_test("obfs4")
        self.service.run_test("shadowsocks")
        comparison = self.service.get_comparison()
        assert "techniques" in comparison
        assert "metrics" in comparison
        assert "rankings" in comparison
        assert len(comparison["techniques"]) == 2

    def test_get_comparison_empty(self):
        """测试获取空对比结果。"""
        comparison = self.service.get_comparison()
        assert comparison["techniques"] == []
        assert comparison["metrics"] == {}

    def test_clear(self):
        """测试清除数据。"""
        self.service.run_test("obfs4")
        assert len(self.service.get_results()) == 1
        self.service.clear()
        assert len(self.service.get_results()) == 0

    def test_detection_difficulty_levels(self):
        """测试检测难度等级。"""
        for _ in range(10):
            result = self.service.run_test("meek")
            assert result["detection_difficulty"] in [d.value for d in DetectionDifficulty]

    def test_detection_rate_ranges(self):
        """测试检测率范围。"""
        for tech in ObfuscationTechnique:
            result = self.service.run_test(tech.value)
            assert 0 <= result["detection_rate"] <= 1
            assert 0 <= result["false_positive_rate"] <= 1


class TestObfuscationTechniqueEnum:
    """混淆技术枚举测试类。"""

    def test_enum_values(self):
        """测试枚举值。"""
        assert ObfuscationTechnique.OBFS4.value == "obfs4"
        assert ObfuscationTechnique.SHADOWSOCKS.value == "shadowsocks"
        assert ObfuscationTechnique.UDP2RAW.value == "udp2raw"
        assert ObfuscationTechnique.MEEK.value == "meek"
        assert ObfuscationTechnique.SNOWFLAKE.value == "snowflake"

    def test_enum_from_value(self):
        """测试从值创建枚举。"""
        assert ObfuscationTechnique("obfs4") == ObfuscationTechnique.OBFS4
        assert ObfuscationTechnique("shadowsocks") == ObfuscationTechnique.SHADOWSOCKS


class TestDetectionDifficultyEnum:
    """检测难度枚举测试类。"""

    def test_enum_values(self):
        """测试枚举值。"""
        assert DetectionDifficulty.TRIVIAL.value == "trivial"
        assert DetectionDifficulty.EASY.value == "easy"
        assert DetectionDifficulty.MEDIUM.value == "medium"
        assert DetectionDifficulty.HARD.value == "hard"
        assert DetectionDifficulty.VERY_HARD.value == "very_hard"


class TestGlobalObfuscationService:
    """全局混淆服务实例测试类。"""

    def test_global_instance(self):
        """测试全局实例。"""
        assert obfuscation_service is not None
        assert isinstance(obfuscation_service, ObfuscationService)