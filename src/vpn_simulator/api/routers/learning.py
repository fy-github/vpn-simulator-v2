import logging
from pathlib import Path
from typing import Any, Optional

import yaml
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/learning")

_rfc_data: dict[str, dict[str, Any]] = {}
_faq_categories: list[dict[str, Any]] = []
_faq_items: list[dict[str, Any]] = []
_learning_paths: list[dict[str, Any]] = []


def _load_learning_data() -> None:
    if _rfc_data:
        return
    config_dir = Path(__file__).parent.parent.parent.parent / "config" / "learning"
    if not config_dir.exists():
        config_dir = Path.cwd() / "config" / "learning"
    if not config_dir.exists():
        logger.warning("Learning config directory not found")
        return

    rfc_file = config_dir / "rfc_references.yaml"
    if rfc_file.exists():
        try:
            with open(rfc_file) as f:
                data = yaml.safe_load(f)
            for proto_id, proto_data in data.get("protocols", {}).items():
                _rfc_data[proto_id] = {
                    "protocol": proto_id,
                    "name": proto_data.get("name", proto_id),
                    "full_name": proto_data.get("full_name", ""),
                    "rfcs": proto_data.get("rfcs", []),
                    "references": proto_data.get("references", []),
                }
            logger.info(f"Loaded RFC references for {len(_rfc_data)} protocols")
        except Exception as e:
            logger.warning(f"Failed to load RFC references: {e}")

    faq_file = config_dir / "faq.yaml"
    if faq_file.exists():
        try:
            with open(faq_file) as f:
                data = yaml.safe_load(f)
            for cat in data.get("categories", []):
                cat_id = cat["id"]
                _faq_categories.append({
                    "id": cat_id,
                    "name": cat.get("name", cat_id),
                    "icon": cat.get("icon", "help-circle"),
                    "question_count": len(cat.get("questions", [])),
                })
                for q in cat.get("questions", []):
                    _faq_items.append({
                        "category_id": cat_id,
                        "category_name": cat.get("name", cat_id),
                        "category_icon": cat.get("icon", "help-circle"),
                        "id": q.get("id", ""),
                        "question": q.get("question", ""),
                        "answer": q.get("answer", ""),
                        "tags": q.get("tags", []),
                    })
            logger.info(f"Loaded {len(_faq_items)} FAQ items in {len(_faq_categories)} categories")
        except Exception as e:
            logger.warning(f"Failed to load FAQ: {e}")

    paths_file = config_dir / "learning_paths.yaml"
    if paths_file.exists():
        try:
            with open(paths_file) as f:
                data = yaml.safe_load(f)
            for path in data.get("paths", []):
                _learning_paths.append({
                    "id": path.get("id", ""),
                    "name": path.get("name", ""),
                    "description": path.get("description", ""),
                    "icon": path.get("icon", "target"),
                    "difficulty": path.get("difficulty", "beginner"),
                    "estimated_hours": path.get("estimated_hours", 0),
                    "target_audience": path.get("target_audience", ""),
                    "protocol_count": len(path.get("protocols", [])),
                    "protocols": path.get("protocols", []),
                    "prerequisites": path.get("prerequisites", []),
                })
            logger.info(f"Loaded {len(_learning_paths)} learning paths")
        except Exception as e:
            logger.warning(f"Failed to load learning paths: {e}")


class RFCReference(BaseModel):
    protocol: str
    protocol_name: str
    number: str = ""
    title: str
    url: str = ""
    description: str = ""
    published: str = ""
    status: str = ""
    type: str = "rfc"


class FAQCategory(BaseModel):
    id: str
    name: str
    icon: str = ""
    question_count: int = 0


class FAQItem(BaseModel):
    category_id: str
    category_name: str
    category_icon: str = ""
    id: str
    question: str
    answer: str
    tags: list[str] = []


class LearningPathSummary(BaseModel):
    id: str
    name: str
    description: str = ""
    icon: str = ""
    difficulty: str = "beginner"
    estimated_hours: int = 0
    target_audience: str = ""
    protocol_count: int = 0


@router.get("/rfc", response_model=list[RFCReference])
async def list_rfc_references(
    protocol: Optional[str] = Query(None),
) -> list[dict[str, Any]]:
    _load_learning_data()
    result = []
    for proto_id, proto in _rfc_data.items():
        if protocol and proto_id != protocol:
            continue
        for rfc in proto.get("rfcs", []):
            result.append({
                "protocol": proto_id,
                "protocol_name": proto["name"],
                "number": rfc.get("number", ""),
                "title": rfc.get("title", ""),
                "url": rfc.get("url", ""),
                "description": rfc.get("description", ""),
                "published": rfc.get("published", ""),
                "status": rfc.get("status", ""),
                "type": "rfc",
            })
        for ref in proto.get("references", []):
            result.append({
                "protocol": proto_id,
                "protocol_name": proto["name"],
                "number": "",
                "title": ref.get("title", ""),
                "url": ref.get("url", ""),
                "description": ref.get("description", ""),
                "published": "",
                "status": "",
                "type": "reference",
            })
    return result


@router.get("/faq", response_model=list[FAQItem])
async def list_faq(
    category: Optional[str] = Query(None),
) -> list[dict[str, Any]]:
    _load_learning_data()
    if category:
        return [item for item in _faq_items if item["category_id"] == category]
    return _faq_items


@router.get("/faq/categories", response_model=list[FAQCategory])
async def list_faq_categories() -> list[dict[str, Any]]:
    _load_learning_data()
    return _faq_categories


@router.get("/paths", response_model=list[LearningPathSummary])
async def list_learning_paths() -> list[dict[str, Any]]:
    _load_learning_data()
    return [
        {k: v for k, v in p.items() if k not in ("protocols", "prerequisites")}
        for p in _learning_paths
    ]


@router.get("/paths/{path_id}")
async def get_learning_path(path_id: str) -> dict[str, Any]:
    _load_learning_data()
    for p in _learning_paths:
        if p["id"] == path_id:
            return p
    raise HTTPException(status_code=404, detail=f"Learning path '{path_id}' not found")
