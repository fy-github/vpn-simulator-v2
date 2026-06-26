"""学习资源服务。

提供 RFC 文档引用、FAQ、学习路径等教学资源的加载和查询功能。
从 YAML 配置文件加载资源定义，为学习者提供结构化的学习内容。

Example:
    >>> service = LearningService(config_path="config/learning")
    >>> rfcs = await service.list_rfc_references()
    >>> faq = await service.list_faq()
    >>> paths = await service.list_learning_paths()
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import structlog
import yaml

logger = structlog.get_logger(__name__)


class LearningService:
    """学习资源服务。

    负责加载和管理学习资源，包括 RFC 文档引用、FAQ 和学习路径。
    从 YAML 配置文件加载资源定义，提供查询接口。

    Attributes:
        _config_path: 学习资源配置文件目录路径。
        _rfc_references: RFC 文档引用映射。
        _faq: FAQ 分类和问题映射。
        _learning_paths: 学习路径映射。
    """

    def __init__(self, config_path: str = "config/learning") -> None:
        """初始化学习资源服务。

        Args:
            config_path: 学习资源配置文件目录路径。
        """
        self._config_path = Path(config_path)
        self._rfc_references: dict[str, Any] = {}
        self._faq: dict[str, Any] = {}
        self._learning_paths: dict[str, Any] = {}
        self._load_resources()

    def _load_resources(self) -> None:
        """从 YAML 文件加载所有学习资源。"""
        if not self._config_path.exists():
            logger.warning("learning_config_path_not_exists", path=str(self._config_path))
            return

        self._load_rfc_references()
        self._load_faq()
        self._load_learning_paths()

        logger.info(
            "learning_resources_loaded",
            rfc_count=len(self._rfc_references),
            faq_categories=len(self._faq.get("categories", [])),
            paths_count=len(self._learning_paths),
        )

    def _load_rfc_references(self) -> None:
        """加载 RFC 文档引用配置。"""
        rfc_file = self._config_path / "rfc_references.yaml"
        if not rfc_file.exists():
            logger.warning("rfc_references_file_not_exists", file=str(rfc_file))
            return

        try:
            with open(rfc_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if data and "protocols" in data:
                self._rfc_references = data["protocols"]
                logger.debug("rfc_references_loaded", count=len(self._rfc_references))
        except Exception as e:
            logger.error("failed_to_load_rfc_references", error=str(e))

    def _load_faq(self) -> None:
        """加载 FAQ 配置。"""
        faq_file = self._config_path / "faq.yaml"
        if not faq_file.exists():
            logger.warning("faq_file_not_exists", file=str(faq_file))
            return

        try:
            with open(faq_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if data:
                self._faq = data
                logger.debug("faq_loaded", categories=len(data.get("categories", [])))
        except Exception as e:
            logger.error("failed_to_load_faq", error=str(e))

    def _load_learning_paths(self) -> None:
        """加载学习路径配置。"""
        paths_file = self._config_path / "learning_paths.yaml"
        if not paths_file.exists():
            logger.warning("learning_paths_file_not_exists", file=str(paths_file))
            return

        try:
            with open(paths_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if data and "paths" in data:
                for path in data["paths"]:
                    path_id = path.get("id")
                    if path_id:
                        self._learning_paths[path_id] = path
                logger.debug("learning_paths_loaded", count=len(self._learning_paths))

                if "milestones" in data:
                    self._milestones = data["milestones"]
        except Exception as e:
            logger.error("failed_to_load_learning_paths", error=str(e))

    async def list_rfc_references(self, protocol: Optional[str] = None) -> list[dict[str, Any]]:
        """获取 RFC 文档引用列表。

        Args:
            protocol: 可选的协议过滤器。

        Returns:
            RFC 文档引用列表。
        """
        result = []

        for protocol_id, protocol_data in self._rfc_references.items():
            if protocol and protocol_id != protocol:
                continue

            rfcs = protocol_data.get("rfcs", [])
            references = protocol_data.get("references", [])

            for rfc in rfcs:
                result.append({
                    "protocol": protocol_id,
                    "protocol_name": protocol_data.get("name", protocol_id),
                    "number": rfc.get("number", ""),
                    "title": rfc.get("title", ""),
                    "url": rfc.get("url", ""),
                    "description": rfc.get("description", ""),
                    "published": rfc.get("published", ""),
                    "status": rfc.get("status", ""),
                    "type": "rfc",
                })

            for ref in references:
                result.append({
                    "protocol": protocol_id,
                    "protocol_name": protocol_data.get("name", protocol_id),
                    "number": "",
                    "title": ref.get("title", ""),
                    "url": ref.get("url", ""),
                    "description": ref.get("description", ""),
                    "published": "",
                    "status": "",
                    "type": "reference",
                })

        return result

    async def get_protocol_rfc_references(self, protocol: str) -> dict[str, Any]:
        """获取指定协议的 RFC 文档引用。

        Args:
            protocol: 协议名称。

        Returns:
            协议的 RFC 文档引用信息。

        Raises:
            ValueError: 协议不存在。
        """
        protocol_data = self._rfc_references.get(protocol)
        if protocol_data is None:
            raise ValueError(f"Protocol '{protocol}' not found in RFC references")

        return {
            "protocol": protocol,
            "name": protocol_data.get("name", protocol),
            "full_name": protocol_data.get("full_name", ""),
            "rfcs": protocol_data.get("rfcs", []),
            "references": protocol_data.get("references", []),
        }

    async def list_faq(self, category: Optional[str] = None) -> list[dict[str, Any]]:
        """获取 FAQ 列表。

        Args:
            category: 可选的分类过滤器。

        Returns:
            FAQ 列表。
        """
        categories = self._faq.get("categories", [])
        result = []

        for cat in categories:
            if category and cat.get("id") != category:
                continue

            questions = cat.get("questions", [])
            for q in questions:
                result.append({
                    "category_id": cat.get("id", ""),
                    "category_name": cat.get("name", ""),
                    "category_icon": cat.get("icon", ""),
                    "id": q.get("id", ""),
                    "question": q.get("question", ""),
                    "answer": q.get("answer", ""),
                    "tags": q.get("tags", []),
                })

        return result

    async def get_faq_categories(self) -> list[dict[str, Any]]:
        """获取 FAQ 分类列表。

        Returns:
            FAQ 分类列表。
        """
        categories = self._faq.get("categories", [])
        return [
            {
                "id": cat.get("id", ""),
                "name": cat.get("name", ""),
                "icon": cat.get("icon", ""),
                "question_count": len(cat.get("questions", [])),
            }
            for cat in categories
        ]

    async def get_faq_item(self, question_id: str) -> Optional[dict[str, Any]]:
        """获取单个 FAQ 项目。

        Args:
            question_id: 问题 ID。

        Returns:
            FAQ 项目信息，不存在返回 None。
        """
        categories = self._faq.get("categories", [])

        for cat in categories:
            for q in cat.get("questions", []):
                if q.get("id") == question_id:
                    return {
                        "category_id": cat.get("id", ""),
                        "category_name": cat.get("name", ""),
                        "category_icon": cat.get("icon", ""),
                        "id": q.get("id", ""),
                        "question": q.get("question", ""),
                        "answer": q.get("answer", ""),
                        "tags": q.get("tags", []),
                    }

        return None

    async def list_learning_paths(self) -> list[dict[str, Any]]:
        """获取学习路径列表。

        Returns:
            学习路径列表。
        """
        result = []
        for path_id, path_data in self._learning_paths.items():
            protocols = path_data.get("protocols", [])
            result.append({
                "id": path_id,
                "name": path_data.get("name", ""),
                "description": path_data.get("description", ""),
                "icon": path_data.get("icon", ""),
                "difficulty": path_data.get("difficulty", ""),
                "estimated_hours": path_data.get("estimated_hours", 0),
                "target_audience": path_data.get("target_audience", ""),
                "protocol_count": len(protocols),
            })

        return result

    async def get_learning_path(self, path_id: str) -> Optional[dict[str, Any]]:
        """获取学习路径详情。

        Args:
            path_id: 学习路径 ID。

        Returns:
            学习路径详情，不存在返回 None。
        """
        path_data = self._learning_paths.get(path_id)
        if path_data is None:
            return None

        return {
            "id": path_id,
            "name": path_data.get("name", ""),
            "description": path_data.get("description", ""),
            "icon": path_data.get("icon", ""),
            "difficulty": path_data.get("difficulty", ""),
            "estimated_hours": path_data.get("estimated_hours", 0),
            "target_audience": path_data.get("target_audience", ""),
            "prerequisites": path_data.get("prerequisites", []),
            "protocols": path_data.get("protocols", []),
        }

    async def get_learning_path_milestones(self, path_id: str) -> list[dict[str, Any]]:
        """获取学习路径的里程碑。

        Args:
            path_id: 学习路径 ID。

        Returns:
            里程碑列表。
        """
        milestones = getattr(self, "_milestones", [])
        return [
            milestone
            for milestone in milestones
            if milestone.get("path_id") == path_id
        ]

    async def search_resources(self, query: str) -> dict[str, Any]:
        """搜索学习资源。

        Args:
            query: 搜索关键词。

        Returns:
            搜索结果，包含匹配的 RFC、FAQ 和学习路径。
        """
        query_lower = query.lower()
        result = {
            "rfc_references": [],
            "faq": [],
            "learning_paths": [],
        }

        # 搜索 RFC 引用
        for protocol_id, protocol_data in self._rfc_references.items():
            for rfc in protocol_data.get("rfcs", []):
                if (
                    query_lower in rfc.get("title", "").lower()
                    or query_lower in rfc.get("description", "").lower()
                    or query_lower in rfc.get("number", "").lower()
                ):
                    result["rfc_references"].append({
                        "protocol": protocol_id,
                        "protocol_name": protocol_data.get("name", protocol_id),
                        "number": rfc.get("number", ""),
                        "title": rfc.get("title", ""),
                        "url": rfc.get("url", ""),
                        "description": rfc.get("description", ""),
                    })

        # 搜索 FAQ
        for cat in self._faq.get("categories", []):
            for q in cat.get("questions", []):
                if (
                    query_lower in q.get("question", "").lower()
                    or query_lower in q.get("answer", "").lower()
                    or any(query_lower in tag.lower() for tag in q.get("tags", []))
                ):
                    result["faq"].append({
                        "category_id": cat.get("id", ""),
                        "category_name": cat.get("name", ""),
                        "id": q.get("id", ""),
                        "question": q.get("question", ""),
                        "answer": q.get("answer", ""),
                        "tags": q.get("tags", []),
                    })

        # 搜索学习路径
        for path_id, path_data in self._learning_paths.items():
            if (
                query_lower in path_data.get("name", "").lower()
                or query_lower in path_data.get("description", "").lower()
                or query_lower in path_data.get("target_audience", "").lower()
            ):
                result["learning_paths"].append({
                    "id": path_id,
                    "name": path_data.get("name", ""),
                    "description": path_data.get("description", ""),
                    "difficulty": path_data.get("difficulty", ""),
                })

        return result
