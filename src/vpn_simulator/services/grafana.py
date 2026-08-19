"""Grafana 集成服务（F6）。

提供内置 Grafana 仪表板（JSON）与 Prometheus 告警规则的加载与查询，
供 `/api/v1/grafana/*` 端点暴露，方便用户一键导入 Grafana。

`/metrics` 端点已在 Phase 0 由 exporters/prometheus 实现，本服务补齐
F6 的"内置仪表板 + 告警规则"两项。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import structlog
import yaml

logger = structlog.get_logger(__name__)

_DASHBOARDS_DIR = Path(__file__).parent.parent.parent.parent / "config" / "grafana" / "dashboards"
_RULES_PATH = (
    Path(__file__).parent.parent.parent.parent / "config" / "grafana" / "alerting" / "rules.yaml"
)


class GrafanaService:
    """Grafana 集成服务。"""

    def __init__(
        self,
        dashboards_dir: Path | None = None,
        rules_path: Path | None = None,
    ) -> None:
        self._dashboards_dir = dashboards_dir or _DASHBOARDS_DIR
        self._rules_path = rules_path or _RULES_PATH

    def list_dashboards(self) -> list[dict[str, Any]]:
        """列出内置仪表板元数据（name/uid/title）。"""
        if not self._dashboards_dir.exists():
            return []
        dashboards = []
        for path in sorted(self._dashboards_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                dashboards.append(
                    {
                        "name": path.stem,
                        "uid": data.get("uid", path.stem),
                        "title": data.get("title", path.stem),
                    }
                )
            except Exception as e:
                logger.error("grafana_dashboard_load_error", path=str(path), error=str(e))
        return dashboards

    def get_dashboard(self, name: str) -> dict[str, Any] | None:
        """返回指定仪表板的完整 JSON 定义。"""
        path = self._dashboards_dir / f"{name}.json"
        if not path.exists():
            return None
        try:
            return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
        except Exception as e:
            logger.error("grafana_dashboard_load_error", path=str(path), error=str(e))
            return None

    def list_alert_rules(self) -> list[dict[str, Any]]:
        """列出告警规则（按 group 组织）。"""
        if not self._rules_path.exists():
            return []
        try:
            data = yaml.safe_load(self._rules_path.read_text(encoding="utf-8")) or {}
            return cast(list[dict[str, Any]], data.get("groups", []))
        except Exception as e:
            logger.error("grafana_rules_load_error", path=str(self._rules_path), error=str(e))
            return []
