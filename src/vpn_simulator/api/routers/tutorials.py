import logging
import time
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tutorials")

_tutorials: dict[str, dict[str, Any]] = {}
_sessions: dict[str, dict[str, Any]] = {}


def _load_tutorials() -> None:
    if _tutorials:
        return
    config_dir = Path(__file__).parent.parent.parent.parent / "config" / "tutorials"
    if not config_dir.exists():
        config_dir = Path.cwd() / "config" / "tutorials"
    if not config_dir.exists():
        logger.warning("Tutorials config directory not found")
        return
    for yaml_file in config_dir.glob("*.yaml"):
        try:
            with open(yaml_file) as f:
                data = yaml.safe_load(f)
            tutorial_id = yaml_file.stem
            _tutorials[tutorial_id] = {
                "id": tutorial_id,
                "name": data.get("name", tutorial_id),
                "protocol": data.get("protocol", ""),
                "description": data.get("description", ""),
                "difficulty": data.get("difficulty", "beginner"),
                "estimated_time": data.get("estimated_time", 10),
                "total_steps": len(data.get("steps", [])),
                "steps": data.get("steps", []),
            }
            logger.info(f"Loaded tutorial: {tutorial_id}")
        except Exception as e:
            logger.warning(f"Failed to load tutorial {yaml_file}: {e}")


class TutorialSummary(BaseModel):
    id: str
    name: str
    protocol: str
    description: str = ""
    difficulty: str = "beginner"
    estimated_time: int = 10
    total_steps: int = 0


class TutorialStepInfo(BaseModel):
    title: str
    description: str
    packet_info: str = ""
    rfc_reference: str = ""
    expected_state: str = ""
    hint: str = ""


class TutorialDetail(BaseModel):
    id: str
    name: str
    protocol: str
    description: str = ""
    difficulty: str = "beginner"
    estimated_time: int = 10
    total_steps: int = 0
    steps: list[TutorialStepInfo] = []


class TutorialSessionState(BaseModel):
    tutorial_id: str
    current_step: int = 0
    total_steps: int = 0
    is_completed: bool = False
    started_at: str = ""
    completed_at: str | None = None
    current_step_info: TutorialStepInfo | None = None
    message: str = ""


def _make_session(tutorial_id: str, step: int = 0) -> dict[str, Any]:
    tutorial = _tutorials[tutorial_id]
    steps = tutorial["steps"]
    total = len(steps)
    completed = step >= total
    current = steps[step] if step < total and steps else None
    return {
        "tutorial_id": tutorial_id,
        "current_step": step,
        "total_steps": total,
        "is_completed": completed,
        "started_at": _sessions.get(tutorial_id, {}).get("started_at", time.strftime("%Y-%m-%dT%H:%M:%S")),
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S") if completed else None,
        "current_step_info": current,
        "message": "Congratulations! Tutorial completed." if completed else "",
    }


@router.get("", response_model=list[TutorialSummary])
async def list_tutorials() -> list[dict[str, Any]]:
    _load_tutorials()
    return [
        {k: v for k, v in t.items() if k != "steps"}
        for t in _tutorials.values()
    ]


@router.get("/{tutorial_id}", response_model=TutorialDetail)
async def get_tutorial(tutorial_id: str) -> dict[str, Any]:
    _load_tutorials()
    if tutorial_id not in _tutorials:
        raise HTTPException(status_code=404, detail=f"Tutorial '{tutorial_id}' not found")
    return _tutorials[tutorial_id]


@router.post("/{tutorial_id}/start", response_model=TutorialSessionState)
async def start_tutorial(tutorial_id: str) -> dict[str, Any]:
    _load_tutorials()
    if tutorial_id not in _tutorials:
        raise HTTPException(status_code=404, detail=f"Tutorial '{tutorial_id}' not found")
    session = _make_session(tutorial_id, 0)
    _sessions[tutorial_id] = session
    return session


@router.post("/{tutorial_id}/next", response_model=TutorialSessionState)
async def next_step(tutorial_id: str) -> dict[str, Any]:
    _load_tutorials()
    if tutorial_id not in _tutorials:
        raise HTTPException(status_code=404, detail=f"Tutorial '{tutorial_id}' not found")
    session = _sessions.get(tutorial_id)
    if not session:
        raise HTTPException(status_code=400, detail="Tutorial not started")
    next_s = min(session["current_step"] + 1, _tutorials[tutorial_id]["total_steps"])
    session = _make_session(tutorial_id, next_s)
    _sessions[tutorial_id] = session
    return session


@router.post("/{tutorial_id}/prev", response_model=TutorialSessionState)
async def prev_step(tutorial_id: str) -> dict[str, Any]:
    _load_tutorials()
    if tutorial_id not in _tutorials:
        raise HTTPException(status_code=404, detail=f"Tutorial '{tutorial_id}' not found")
    session = _sessions.get(tutorial_id)
    if not session:
        raise HTTPException(status_code=400, detail="Tutorial not started")
    prev_s = max(session["current_step"] - 1, 0)
    session = _make_session(tutorial_id, prev_s)
    _sessions[tutorial_id] = session
    return session


@router.post("/{tutorial_id}/reset", response_model=TutorialSessionState)
async def reset_tutorial(tutorial_id: str) -> dict[str, Any]:
    _load_tutorials()
    if tutorial_id not in _tutorials:
        raise HTTPException(status_code=404, detail=f"Tutorial '{tutorial_id}' not found")
    session = _make_session(tutorial_id, 0)
    _sessions[tutorial_id] = session
    return session
