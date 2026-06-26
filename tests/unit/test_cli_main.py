"""Tests for CLI __main__ module."""

from __future__ import annotations

import subprocess
import sys

import pytest


class TestCLIMain:
    def test_main_import(self):
        from vpn_simulator.cli.__main__ import main
        assert callable(main)

    def test_module_execution(self):
        result = subprocess.run(
            [sys.executable, "-m", "vpn_simulator.cli", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "VPN Simulator" in result.stdout

    def test_module_version(self):
        result = subprocess.run(
            [sys.executable, "-m", "vpn_simulator.cli", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "2.0.0" in result.stdout
