"""多厂商 CLI 服务模块。

支持 Cisco IOS 和华为 VRP 命令语法，将命令映射到内部 API。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


class VendorType(Enum):
    """厂商类型枚举。"""
    CISCO = "cisco"
    HUAWEI = "huawei"


class CommandMode(Enum):
    """命令模式枚举。"""
    USER = "user"           # 用户模式
    PRIVILEGED = "privileged"  # 特权模式
    CONFIG = "config"       # 配置模式
    INTERFACE = "interface"  # 接口配置模式


@dataclass
class CommandMapping:
    """命令映射定义。"""
    vendor_command: str     # 厂商命令
    internal_action: str    # 内部动作
    description: str        # 命令描述
    mode: CommandMode       # 所需模式
    aliases: list[str] = field(default_factory=list)  # 别名


@dataclass
class CommandResult:
    """命令执行结果。"""
    command: str
    output: str
    success: bool
    timestamp: datetime = field(default_factory=datetime.now)


class VendorCLIService:
    """多厂商 CLI 服务。"""

    def __init__(self) -> None:
        """初始化多厂商 CLI 服务。"""
        self._history: list[CommandResult] = []
        self._cisco_commands = self._init_cisco_commands()
        self._huawei_commands = self._init_huawei_commands()

    def _init_cisco_commands(self) -> dict[str, CommandMapping]:
        """初始化 Cisco IOS 命令映射。"""
        commands = {
            "show ip interface brief": CommandMapping(
                vendor_command="show ip interface brief",
                internal_action="show_interfaces_brief",
                description="显示接口摘要信息",
                mode=CommandMode.USER,
                aliases=["sh ip int br", "show ip int brief"]
            ),
            "show ip route": CommandMapping(
                vendor_command="show ip route",
                internal_action="show_routes",
                description="显示 IP 路由表",
                mode=CommandMode.USER,
                aliases=["sh ip ro"]
            ),
            "show interfaces": CommandMapping(
                vendor_command="show interfaces",
                internal_action="show_interfaces_detail",
                description="显示接口详细信息",
                mode=CommandMode.USER,
                aliases=["sh int"]
            ),
            "show running-config": CommandMapping(
                vendor_command="show running-config",
                internal_action="show_running_config",
                description="显示运行配置",
                mode=CommandMode.PRIVILEGED,
                aliases=["sh run"]
            ),
            "configure terminal": CommandMapping(
                vendor_command="configure terminal",
                internal_action="enter_config_mode",
                description="进入配置模式",
                mode=CommandMode.PRIVILEGED,
                aliases=["conf t", "config t"]
            ),
            "write memory": CommandMapping(
                vendor_command="write memory",
                internal_action="save_config",
                description="保存配置",
                mode=CommandMode.PRIVILEGED,
                aliases=["wr mem", "copy running-config startup-config"]
            ),
            "ping": CommandMapping(
                vendor_command="ping",
                internal_action="ping",
                description="测试连通性",
                mode=CommandMode.USER
            ),
            "traceroute": CommandMapping(
                vendor_command="traceroute",
                internal_action="traceroute",
                description="路由追踪",
                mode=CommandMode.USER,
                aliases=["trace"]
            ),
        }
        return commands

    def _init_huawei_commands(self) -> dict[str, CommandMapping]:
        """初始化华为 VRP 命令映射。"""
        commands = {
            "display ip interface brief": CommandMapping(
                vendor_command="display ip interface brief",
                internal_action="show_interfaces_brief",
                description="显示接口摘要信息",
                mode=CommandMode.USER,
                aliases=["dis ip int br"]
            ),
            "display ip routing-table": CommandMapping(
                vendor_command="display ip routing-table",
                internal_action="show_routes",
                description="显示 IP 路由表",
                mode=CommandMode.USER,
                aliases=["dis ip ro"]
            ),
            "display interface": CommandMapping(
                vendor_command="display interface",
                internal_action="show_interfaces_detail",
                description="显示接口详细信息",
                mode=CommandMode.USER,
                aliases=["dis int"]
            ),
            "display current-configuration": CommandMapping(
                vendor_command="display current-configuration",
                internal_action="show_running_config",
                description="显示运行配置",
                mode=CommandMode.USER,
                aliases=["dis cur"]
            ),
            "system-view": CommandMapping(
                vendor_command="system-view",
                internal_action="enter_config_mode",
                description="进入配置模式",
                mode=CommandMode.USER,
                aliases=["sys"]
            ),
            "save": CommandMapping(
                vendor_command="save",
                internal_action="save_config",
                description="保存配置",
                mode=CommandMode.CONFIG
            ),
            "ping": CommandMapping(
                vendor_command="ping",
                internal_action="ping",
                description="测试连通性",
                mode=CommandMode.USER
            ),
            "tracert": CommandMapping(
                vendor_command="tracert",
                internal_action="traceroute",
                description="路由追踪",
                mode=CommandMode.USER
            ),
        }
        return commands

    def get_supported_commands(self, vendor: VendorType) -> list[dict[str, Any]]:
        """获取支持的命令列表。"""
        commands = self._cisco_commands if vendor == VendorType.CISCO else self._huawei_commands
        return [
            {
                "command": cmd.vendor_command,
                "description": cmd.description,
                "mode": cmd.mode.value,
                "aliases": cmd.aliases
            }
            for cmd in commands.values()
        ]

    def execute_command(
        self,
        vendor: VendorType,
        command: str,
        params: Optional[dict[str, Any]] = None
    ) -> CommandResult:
        """执行厂商命令。"""
        commands = self._cisco_commands if vendor == VendorType.CISCO else self._huawei_commands

        # 查找命令映射
        mapping = None
        for cmd_pattern, cmd_mapping in commands.items():
            if command.lower().startswith(cmd_pattern.lower()):
                mapping = cmd_mapping
                break
            if command.lower() in [a.lower() for a in cmd_mapping.aliases]:
                mapping = cmd_mapping
                break

        if not mapping:
            result = CommandResult(
                command=command,
                output=f"% Unknown command: {command}",
                success=False
            )
            self._history.append(result)
            return result

        # 模拟执行
        output = self._simulate_execution(mapping, params or {})
        result = CommandResult(
            command=command,
            output=output,
            success=True
        )
        self._history.append(result)

        logger.info(
            "command_executed",
            vendor=vendor.value,
            command=command,
            action=mapping.internal_action
        )

        return result

    def _simulate_execution(self, mapping: CommandMapping, params: dict[str, Any]) -> str:
        """模拟命令执行。"""
        action = mapping.internal_action

        if action == "show_interfaces_brief":
            return self._mock_interfaces_brief()
        elif action == "show_routes":
            return self._mock_routes()
        elif action == "show_interfaces_detail":
            return self._mock_interfaces_detail()
        elif action == "show_running_config":
            return self._mock_running_config()
        elif action == "ping":
            target = params.get("target", "10.0.0.1")
            return self._mock_ping(target)
        elif action == "traceroute":
            target = params.get("target", "10.0.0.1")
            return self._mock_traceroute(target)
        elif action == "enter_config_mode":
            return "Enter configuration commands, one per line. End with CNTL/Z."
        elif action == "save_config":
            return "Configuration saved successfully."
        else:
            return f"Command '{mapping.vendor_command}' executed successfully."

    def _mock_interfaces_brief(self) -> str:
        import subprocess
        try:
            result = subprocess.run(['ip', '-brief', 'addr'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                output = "Interface              IP-Address      OK? Method Status                Protocol\n"
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 3:
                        name = parts[0]
                        state = parts[1] if len(parts) > 1 else 'unknown'
                        ip = parts[2] if len(parts) > 2 else 'unassigned'
                        output += f"{name:<22} {ip:<15} YES manual {state:<20} up\n"
                return output
        except Exception:
            pass
        return "Interface              IP-Address      OK? Method Status                Protocol\nlo                     127.0.0.1       YES manual up                    up\neth0                   192.168.1.100   YES manual up                    up"

    def _mock_routes(self) -> str:
        import subprocess
        try:
            result = subprocess.run(['ip', 'route'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout
        except Exception:
            pass
        return "default via 192.168.1.1 dev eth0\n192.168.1.0/24 dev eth0 scope link"

    def _mock_interfaces_detail(self) -> str:
        import subprocess
        try:
            result = subprocess.run(['ip', 'addr', 'show'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout
        except Exception:
            pass
        return "1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN\n    inet 127.0.0.1/8 scope host lo\n2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 state UP\n    inet 192.168.1.100/24 brd 192.168.1.255 scope global eth0"

    def _mock_running_config(self) -> str:
        import subprocess
        try:
            result = subprocess.run(['ip', 'addr', 'show'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                output = "Building configuration...\n\nCurrent configuration:\n!\nhostname VPN-Simulator\n!\n"
                for line in result.stdout.strip().split('\n'):
                    if 'inet ' in line:
                        output += f"interface {line.split(':')[0].strip()}\n"
                        output += f" ip address {line.split('inet ')[1].split(' ')[0]}\n"
                        output += " no shutdown\n!\n"
                output += "end"
                return output
        except Exception:
            pass
        return "Building configuration...\n!\nhostname VPN-Simulator\n!\ninterface eth0\n ip address 192.168.1.100/24\n no shutdown\n!\nend"

    def _mock_ping(self, target: str) -> str:
        import subprocess
        try:
            result = subprocess.run(['ping', '-c', '4', '-W', '2', target], capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                stats = [l for l in lines if 'packet loss' in l or 'rtt' in l or 'round-trip' in l]
                return f"PING {target}:\n" + '\n'.join(lines[-5:])
        except Exception:
            pass
        return f"PING {target}: 5 packets sent, 5 received, 0% packet loss"

    def _mock_traceroute(self, target: str) -> str:
        import subprocess
        try:
            result = subprocess.run(['traceroute', '-m', '5', '-w', '2', target], capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return result.stdout
        except Exception:
            pass
        return f"traceroute to {target}, 5 hops max\n 1  gateway  1.234 ms  1.123 ms  1.045 ms\n 2  {target}  2.345 ms  2.234 ms  2.123 ms"

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """获取命令历史。"""
        return [
            {
                "command": r.command,
                "output": r.output,
                "success": r.success,
                "timestamp": r.timestamp.isoformat()
            }
            for r in self._history[-limit:]
        ]


# 全局实例
_vendor_cli_service: Optional[VendorCLIService] = None


def get_vendor_cli_service() -> VendorCLIService:
    """获取多厂商 CLI 服务实例。"""
    global _vendor_cli_service
    if _vendor_cli_service is None:
        _vendor_cli_service = VendorCLIService()
    return _vendor_cli_service
