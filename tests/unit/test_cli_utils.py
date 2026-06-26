"""Tests for CLI utils - targeted coverage for uncovered lines."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from vpn_simulator.cli.utils import confirm_action, handle_error, handle_success, output_json, output_table


class TestOutputTable:
    def test_output_table_json_mode(self):
        output_table(
            title="Test",
            columns=["Name", "Value"],
            rows=[["a", "1"], ["b", "2"]],
            json_output=True,
        )

    def test_output_table_rich_mode(self):
        output_table(
            title="Test",
            columns=["Name", "Value"],
            rows=[["a", "1"], ["b", "2"]],
            json_output=False,
        )


class TestHandleSuccess:
    def test_handle_success_json(self):
        handle_success("ok", json_output=True)

    def test_handle_success_rich(self):
        handle_success("ok", json_output=False)


class TestConfirmAction:
    def test_confirm_action_abort_false(self):
        with patch("click.confirm", return_value=True):
            result = confirm_action("Continue?", abort=False)
            assert result is True

    def test_confirm_action_abort_false_no(self):
        with patch("click.confirm", return_value=False):
            result = confirm_action("Continue?", abort=False)
            assert result is False


import click
