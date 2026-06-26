from __future__ import annotations

from enum import Enum
from typing import Any, Optional


class VXLANState(str, Enum):
    IDLE = "idle"
    INTERFACE_CREATED = "interface_created"
    PEER_DISCOVERED = "peer_discovered"
    TUNNEL_ESTABLISHED = "tunnel_establishED"
    FORWARDING = "forwarding"
    ERROR = "error"


class VXLANStateMachine:
    def __init__(self, vni: int = 100, port: int = 4789) -> None:
        self._state = VXLANState.IDLE
        self._vni = vni
        self._port = port
        self._peers: list[str] = []
        self._packets_forwarded = 0

    @property
    def current_state(self) -> str:
        return self._state.value

    def create_interface(self) -> bool:
        if self._state == VXLANState.IDLE:
            self._state = VXLANState.INTERFACE_CREATED
            return True
        return False

    def add_peer(self, peer_ip: str) -> bool:
        if self._state in (VXLANState.INTERFACE_CREATED, VXLANState.PEER_DISCOVERED):
            if peer_ip not in self._peers:
                self._peers.append(peer_ip)
            self._state = VXLANState.PEER_DISCOVERED
            return True
        return False

    def establish_tunnel(self) -> bool:
        if self._state == VXLANState.PEER_DISCOVERED and self._peers:
            self._state = VXLANState.TUNNEL_ESTABLISHED
            return True
        return False

    def start_forwarding(self) -> bool:
        if self._state == VXLANState.TUNNEL_ESTABLISHED:
            self._state = VXLANState.FORWARDING
            return True
        return False

    def forward_packet(self) -> bool:
        if self._state == VXLANState.FORWARDING:
            self._packets_forwarded += 1
            return True
        return False

    def get_visualization_data(self) -> dict[str, Any]:
        return {
            "current_state": self._state.value,
            "vni": self._vni,
            "port": self._port,
            "peers": self._peers,
            "packets_forwarded": self._packets_forwarded,
        }
