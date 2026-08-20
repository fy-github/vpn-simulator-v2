# VPN Simulator v2

Multi-protocol VPN Server Simulator with modern Web UI — supports **9 VPN/tunnel protocols** for teaching, testing, and security research.
<img width="1911" height="837" alt="image" src="https://github.com/user-attachments/assets/fa5fe893-2e4a-4aac-b238-eeeef8ea6a2e" />


## Features

### Protocol Support

| Protocol | Port | Transport | Status |
|----------|------|-----------|--------|
| PPTP | 1723 | TCP + GRE | Implemented |
| L2TP | 1701 | UDP | Implemented |
| OpenVPN | 1194 | UDP | Implemented |
| IPSec (IKEv1) | 500 / 4500 | UDP | Implemented |
| IKEv2/IPSec | 500 / 4500 | UDP | Implemented |
| WireGuard | 51820 | UDP | Implemented |
| VXLAN | 4789 | UDP (MAC-in-UDP) | Implemented |
| SSTP | 443 | TCP | Implemented |
| OpenConnect | 443 | TCP | Implemented |

### Web UI

- **Dashboard** — Real-time system stats (CPU, memory, uptime), protocol status grid, quick actions
- **Protocol Management** — Start/stop protocols, per-protocol configuration dialogs with tabs
- **Connection Management** — Active connections table, protocol filter, disconnect controls
- **Performance Metrics** — Throughput, latency, packet loss, connection charts with Chart.js
- **Traffic Visualization** — Real-time packet flow animation via WebSocket
- **Fault Injection** — Network, protocol, authentication, encryption fault simulation
- **Attack Simulation** — DoS, MITM, replay, brute force, injection attack testing
- **Scenario Engine** — Predefined network scenarios (3G, satellite, WiFi, wired)
- **Tutorial System** — Step-by-step protocol handshake tutorials for all 9 protocols
- **Learning Resources** — RFC references, FAQ, learning paths
- **Protocol Comparison** — Side-by-side protocol state machine comparison
- **DPI (Deep Packet Inspection)** — Protocol identification and traffic classification
- **IoT Simulator** — Smart home device simulation with MQTT/CoAP
- **Voice Simulator** — VoIP call simulation with codec support
- **Obfuscation Testing** — Traffic obfuscation technique testing
- **Vendor CLI** — Cisco IOS and Huawei VRP command simulation
- **DHCP Simulation** — Spoof random MAC addresses to concurrently acquire DHCP leases (with 802.1Q VLAN tagging and explicit release)
- **Network Impairment** — Time-varying impairment presets/curves (linear/exponential/step/sine/random) applied to real packet flow
- **Config Validation** — 7-step VPN config validation (syntax/port/handshake/auth/tunnel/latency/throughput) for 6 protocols; WireGuard does a real Noise handshake + ChaCha20-Poly1305 data-plane round-trip, OpenVPN does a real control-channel `--tls-auth` HMAC handshake + AES-256-GCM data-plane round-trip
- **PCAP Replay** — Upload PCAP/PCAPNG, replay at 0.5x–10x with protocol filter and session status
- **Routing Protocols** — OSPF/BGP neighbor state machines and routing tables across 4 simulated routers
- **SNMP Simulation** — 12 device types (v2c/v3), MIB-II OID GET/WALK
- **Grafana** — Built-in dashboard JSON and Prometheus alert rules for one-click import
- **Scale Devices** — Lazy 30,000-device simulation with aggregate stats, bulk poll, snapshot persistence
- **C2 Scenarios** — 6 C2 attack scenarios (educational/defensive only) with detection indicators and ethics declaration
- **Data Retention** — packets/state_transitions retention cleanup (max-rows + TTL)

### Tech Stack

**Backend:**
- Python 3.11+ + FastAPI
- SQLAlchemy + aiosqlite (async SQLite)
- Structlog (structured logging)
- Pydantic v2 (data validation)
- Plugin architecture with dynamic loading

**Frontend:**
- React 18 + TypeScript
- Vite 5 (build tool)
- Tailwind CSS 3 (styling)
- Chart.js (charts)
- GSAP (animations)
- i18next (internationalization)
- Custom UI component library (Card, Button, Badge, Input, Select, Dialog, Tabs, Progress)

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- npm or yarn

### Installation

```bash
# Clone the repository
git clone https://github.com/fy-github/vpn-simulator-v2.git
cd vpn-simulator-v2

# Install Python dependencies (recommended: uv, reads the locked uv.lock)
uv sync --extra dev

# — or with pip + requirements.txt —
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt        # runtime dependencies
pip install -r requirements-dev.txt    # + dev/test dependencies

# Install frontend dependencies
cd web-ui && npm install && cd ..
```

> **国内镜像（可选）：** 若 PyPI（`files.pythonhosted.org`）下载缓慢，可用清华镜像：
> ```bash
> export UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple   # uv
> pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple   # pip
> ```

### Running

```bash
# Start backend API server (默认仅监听本机；如需对外暴露请显式 --host 0.0.0.0 并配置 VPN_SIM_API_KEY)
.venv/bin/python -m uvicorn vpn_simulator.api.app:app --host 127.0.0.1 --port 8080

# In another terminal, start frontend dev server
cd web-ui && npm run dev
```

Open http://localhost:3000 in your browser.

### Production Build

```bash
cd web-ui && npm run build
```

The built files will be in `web-ui/dist/`.

## Dependency Management

`pyproject.toml` is the single source of truth for Python dependencies (PEP 621). Three derived files keep installs reproducible:

| File | Purpose |
|------|---------|
| `uv.lock` | Fully-resolved lockfile (all transitive deps pinned). Used by `uv sync`. |
| `requirements.txt` | Pinned runtime dependencies, exported from `uv.lock` for `pip` users. |
| `requirements-dev.txt` | Runtime + dev/test dependencies (pytest, ruff, black, mypy, …). |

Regenerate after editing `pyproject.toml`:

```bash
uv lock                                   # re-resolve uv.lock
uv export --no-hashes --no-dev -o requirements.txt
uv export --no-hashes --extra dev -o requirements-dev.txt
```

## Project Structure

```
vpn-simulator-v2/
├── src/
│   └── vpn_simulator/
│       ├── api/              # FastAPI routes and middleware
│       │   ├── routers/      # API endpoint handlers
│       │   ├── app.py        # FastAPI application
│       │   └── websocket.py  # WebSocket manager
│       ├── cli/              # CLI commands
│       ├── core/             # Core modules (config, database, events)
│       ├── domain/           # Domain models
│       ├── plugins/          # Plugin system (protocol, fault, attack)
│       └── services/         # Business logic services
├── web-ui/
│   ├── src/
│   │   ├── api/              # API client
│   │   ├── components/       # React components
│   │   │   └── ui/           # UI component library
│   │   ├── locales/          # i18n translations (zh-CN, en)
│   │   └── pages/            # Page components
│   └── vite.config.ts        # Vite configuration
├── config/
│   ├── tutorials/            # Tutorial YAML files (8 protocols)
│   ├── learning/             # Learning resources (RFC, FAQ, paths)
│   └── scenarios/            # Network scenario presets
└── tests/
    ├── unit/                 # Unit tests
    ├── integration/          # API integration tests
    └── e2e/                  # End-to-end tests
```

## Persistence & State

The backend initializes a SQLite database (SQLAlchemy + aiosqlite) on startup
and creates `vpn_simulator.db` with all tables automatically. Note that the
simulator currently keeps its live protocol/connection state **in memory**
(per-process); the database layer is initialized and available to the services,
but it is not yet the single source of truth for live protocol/connection state.

## API Endpoints

| Category | Endpoints |
|----------|-----------|
| Protocols | `GET/POST /api/v1/protocols`, `POST /api/v1/protocols/{name}/start\|stop` |
| Connections | `GET /api/v1/connections`, `DELETE /api/v1/connections/{id}` |
| Faults | `GET/POST /api/v1/faults`, `DELETE /api/v1/faults/{id}` |
| Attacks | `GET/POST /api/v1/attacks`, `DELETE /api/v1/attacks/{id}` |
| Stats | `GET /api/v1/stats` (real CPU/memory via psutil) |
| Metrics | `GET /api/v1/metrics/throughput\|latency\|packet-loss\|connections` |
| Scenarios | `GET/POST /api/v1/scenarios`, `POST /api/v1/scenarios/{id}/apply` |
| Tutorials | `GET /api/v1/tutorials`, `POST /api/v1/tutorials/{id}/start\|next\|prev\|reset` |
| Learning | `GET /api/v1/learning/rfc\|faq\|paths` |
| Traffic | `POST /api/v1/traffic/capture\|stop`, `WS /api/v1/traffic/stream` |
| DPI | `GET /api/v1/dpi/protocols\|statistics` |
| IoT | `GET /api/v1/iot/devices` |
| Voice | `POST /api/v1/voice/calls` |
| Obfuscation | `GET /api/v1/obfuscation/techniques` |
| Vendor CLI | `POST /api/v1/vendor-cli/execute` |
| DHCP | `POST /api/v1/dhcp/start\|stop\|release`, `GET /api/v1/dhcp/status\|leases` |
| Impairment | `GET/POST /api/v1/impairments`, `POST /api/v1/impairments/presets/{name}/apply`, `GET /api/v1/impairments/{id}/status\|timeline` |
| Validation | `POST /api/v1/validation/validate\|batch`, `GET /api/v1/validation/history` |
| PCAP | `POST /api/v1/pcap/upload\|replay`, `GET /api/v1/pcap/files\|status/{id}\|stats/{id}` |
| SNMP | `GET /api/v1/snmp/devices\|oids`, `GET /api/v1/snmp/devices/{id}/get\|walk` |
| Routing | `GET /api/v1/routing/routers\|{id}/routes`, `GET /api/v1/routing/{id}/neighbors`, `POST /api/v1/routing/{id}/neighbors/{n}/establish` |
| Grafana | `GET /api/v1/grafana/dashboards\|alert-rules`, `GET /api/v1/grafana/dashboards/{name}` |
| Scale | `GET /api/v1/scale/devices\|stats\|snapshots`, `POST /api/v1/scale/poll\|persist` |
| C2 | `GET /api/v1/c2/scenarios\|ethics\|scenarios/{id}\|scenarios/{id}/detection`, `POST /api/v1/c2/scenarios/{id}/simulate` |
| Retention | `GET /api/v1/retention/status`, `POST /api/v1/retention/cleanup` |

## Testing

```bash
# Run all tests
uv run pytest tests/ -q

# Run with coverage (CI enforces a 78% floor)
uv run pytest tests/ --cov=vpn_simulator --cov-report=term --cov-fail-under=78

# Frontend unit tests (vitest)
cd web-ui && npm test

# TypeScript type check
cd web-ui && npx tsc --noEmit

# Production build
cd web-ui && npm run build
```

**Test Results:** 1221 tests passing, 80.7% coverage (Python 3.11, deps pinned by `uv.lock`).

## Lint

CI 全量启用 `ruff check`、`black --check`、eslint 门禁（见 `.github/workflows/ci.yml`）。
本地复现：

```bash
uv run ruff check src tests && uv run black --check src tests   # 后端
cd web-ui && npm run lint                                        # 前端
```

## Configuration

### Protocol Configuration

Each protocol has a dedicated configuration dialog accessible from the Protocols page. Configuration includes:

- **PPTP** — Users, MRU/MTU, IP pool, DNS, auth method
- **L2TP** — Users, MRU/MTU, PSK, identifiers, IP pool, IPSec toggle
- **OpenVPN** — Auth method, users, tunnel type, cipher, certificates, routes
- **IPSec** — Auth type (PSK/cert), Phase1/Phase2 parameters
- **IKEv2** — Auth method, IP pool, encryption/DH parameters
- **WireGuard** — Tunnel IP, private/public keys
- **VXLAN** — VNI, local/remote VTEP addresses, MTU
- **SSTP** — Users, MTU, IP pool, DNS, certificates
- **OpenConnect** — Users, tunnel type, MTU, IP pool, certificates

### Tutorial System

Tutorials are defined in YAML files under `config/tutorials/`. Each tutorial contains:

```yaml
name: "PPTP Basics"
protocol: pptp
description: "Learn the complete PPTP handshake flow"
difficulty: beginner
estimated_time: 15
steps:
  - title: "Send SCCRQ"
    description: "Client initiates control connection..."
    packet_info: "SCCRQ packet contains protocol version..."
    rfc_reference: "RFC 2637 Section 3.1"
    expected_state: "WAIT_SCCRP"
    hint: "SCCRQ is the starting point of PPTP..."
```

## License

MIT License — See [LICENSE](LICENSE) for details.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
