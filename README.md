# VPN Simulator v2

Multi-protocol VPN Server Simulator with modern Web UI — supports **8 VPN protocols** for teaching, testing, and security research.
![Uploading image.png…]()

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
- **Tutorial System** — Step-by-step protocol handshake tutorials for all 8 protocols
- **Learning Resources** — RFC references, FAQ, learning paths
- **Protocol Comparison** — Side-by-side protocol state machine comparison
- **DPI (Deep Packet Inspection)** — Protocol identification and traffic classification
- **IoT Simulator** — Smart home device simulation with MQTT/CoAP
- **Voice Simulator** — VoIP call simulation with codec support
- **Obfuscation Testing** — Traffic obfuscation technique testing
- **Vendor CLI** — Cisco IOS and Huawei VRP command simulation

### Tech Stack

**Backend:**
- Python 3.12 + FastAPI
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

- Python 3.12+
- Node.js 18+
- npm or yarn

### Installation

```bash
# Clone the repository
git clone https://github.com/fy-github/vpn-simulator-v2.git
cd vpn-simulator-v2

# Create Python virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd web-ui && npm install && cd ..
```

### Running

```bash
# Start backend API server
.venv/bin/python -m uvicorn vpn_simulator.api.app:app --host 0.0.0.0 --port 8000

# In another terminal, start frontend dev server
cd web-ui && npm run dev
```

Open http://localhost:5174 in your browser.

### Production Build

```bash
cd web-ui && npm run build
```

The built files will be in `web-ui/dist/`.

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

## Testing

```bash
# Run all tests
.venv/bin/python -m pytest tests/ -q

# Run with coverage
.venv/bin/python -m pytest tests/ --cov=vpn_simulator --cov-report=term

# TypeScript type check
cd web-ui && npx tsc --noEmit

# Production build
cd web-ui && npm run build
```

**Test Results:** 1022 tests passing, 90% coverage

## Configuration

### Protocol Configuration

Each protocol has a dedicated configuration dialog accessible from the Protocols page. Configuration includes:

- **PPTP** — Users, MRU/MTU, IP pool, DNS, auth method
- **L2TP** — Users, MRU/MTU, PSK, identifiers, IP pool, IPSec toggle
- **OpenVPN** — Auth method, users, tunnel type, cipher, certificates, routes
- **IPSec** — Auth type (PSK/cert), Phase1/Phase2 parameters
- **IKEv2** — Auth method, IP pool, encryption/DH parameters
- **WireGuard** — Tunnel IP, private/public keys
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
