# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of VPN Simulator v2
- Multi-protocol support: PPTP, L2TP, OpenVPN, IPSec, IKEv2, WireGuard
- Plugin system with dynamic loading
- Protocol state machine visualization
- Network fault injection (latency, packet loss, bandwidth, reorder, duplicate, corrupt)
- Attack simulation (MITM, replay, brute force, downgrade, traffic analysis)
- REST API with FastAPI
- WebSocket real-time events
- CLI with Click and Rich
- Web UI with React, TypeScript, and Tailwind CSS
- Comprehensive test suite (189 tests)
- Docker support
- CI/CD with GitHub Actions

### Changed
- Migrated from PyQt5 to Web-based UI
- Refactored to plugin architecture
- Added cross-platform support (Windows, macOS, Linux)

## [1.0.0] - 2024-01-01

### Added
- Initial release
- Basic VPN protocol simulation
- PyQt5 GUI

---

## Types of Changes

- **Added** for new features.
- **Changed** for changes in existing functionality.
- **Deprecated** for soon-to-be removed features.
- **Removed** for now removed features.
- **Fixed** for any bug fixes.
- **Security** in case of vulnerabilities.
