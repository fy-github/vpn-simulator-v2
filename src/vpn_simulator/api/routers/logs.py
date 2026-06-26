import logging
import time
from collections import deque
from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/logs")

_log_buffer: deque[dict[str, Any]] = deque(maxlen=1000)


class LogHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        _log_buffer.append({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(record.created)),
            "level": record.levelname,
            "message": record.getMessage(),
            "protocol": getattr(record, 'protocol', None),
            "connection_id": getattr(record, 'connection_id', None),
            "extra": {},
        })


_handler = LogHandler()
_handler.setLevel(logging.INFO)
logging.getLogger().addHandler(_handler)
logging.getLogger("vpn_simulator").addHandler(_handler)


class LogEntry(BaseModel):
    timestamp: str
    level: str
    message: str
    protocol: Optional[str] = None
    connection_id: Optional[str] = None
    extra: dict[str, Any] = Field(default_factory=dict)


@router.get(
    "",
    response_model=list[LogEntry],
    summary="Get logs",
)
async def get_logs(
    protocol: Optional[str] = None,
    level: Optional[str] = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    logs = list(_log_buffer)
    if protocol:
        logs = [l for l in logs if l.get("protocol") == protocol]
    if level:
        logs = [l for l in logs if l["level"] == level.upper()]
    return logs[-limit:]
