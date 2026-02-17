"""Tests for pipeline/shared/cli_utils.py (T054).

Verifies:
- style() returns ANSI-wrapped text when colour enabled
- style() returns plain text when colour disabled via set_use_color(False)
- create_sigint_handler() calls callback and exits with 130
- print_help_banner() outputs all 8 sections
- enable_windows_ansi() runs without error on Windows
"""

from __future__ import annotations

import signal
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure shared module is importable
_shared_root = Path(__file__).resolve().parent.parent
if str(_shared_root) not in sys.path:
    sys.path.insert(0, str(_shared_root))

import cli_utils

# -----------------------------------------------------------------------
# style() tests
# -----------------------------------------------------------------------


class TestStyle:
    """Verify ANSI wrapping behaviour."""

    def setup_method(self):
        cli_utils.set_use_color(True)

    def teardown_method(self):
        cli_utils.set_use_color(True)

    def test_returns_ansi_when_color_enabled(self):
        result = cli_utils.style("hello", "green")
        assert "\033[32m" in result
        assert "hello" in result
        assert "\033[0m" in result

    def test_returns_plain_when_color_disabled(self):
        cli_utils.set_use_color(False)
        result = cli_utils.style("hello", "green", "bold")
        assert result == "hello"
        assert "\033[" not in result

    def test_multiple_codes(self):
        result = cli_utils.style("warn", "bold", "yellow")
        assert "\033[1m" in result
        assert "\033[33m" in result

    def test_no_codes_returns_plain(self):
        result = cli_utils.style("plain")
        assert result == "plain"

    def test_unknown_code_ignored(self):
        result = cli_utils.style("x", "nonexistent")
        assert result == "x"


# -----------------------------------------------------------------------
# create_sigint_handler() tests
# -----------------------------------------------------------------------


class TestSigintHandler:
    """Verify handler calls callback and exits 130."""

    def setup_method(self):
        cli_utils.set_use_color(False)

    def teardown_method(self):
        cli_utils.set_use_color(True)

    def test_handler_exits_130(self):
        handler = cli_utils.create_sigint_handler("test_script")
        with pytest.raises(SystemExit) as exc:
            handler(signal.SIGINT, None)
        assert exc.value.code == 130

    def test_handler_calls_callback(self):
        cb = MagicMock()
        handler = cli_utils.create_sigint_handler("test", callback=cb)
        with pytest.raises(SystemExit):
            handler(signal.SIGINT, None)
        cb.assert_called_once()

    def test_handler_prints_abort_banner(self, capsys):
        handler = cli_utils.create_sigint_handler("myscript")
        with pytest.raises(SystemExit):
            handler(signal.SIGINT, None)
        captured = capsys.readouterr()
        assert "ABGEBROCHEN" in captured.err
        assert "myscript" in captured.err


# -----------------------------------------------------------------------
# print_help_banner() tests
# -----------------------------------------------------------------------


class TestPrintHelpBanner:
    """Verify 8-section help output."""

    def setup_method(self):
        cli_utils.set_use_color(False)

    def teardown_method(self):
        cli_utils.set_use_color(True)

    def test_all_sections_present(self, capsys):
        cli_utils.print_help_banner(
            what="Test tool",
            usage="python test.py",
            parameters="--input FILE",
            options="--verbose",
            examples="python test.py --input a.txt",
            configuration="env.yaml",
            output="results/",
            exit_codes="0=OK, 1=Error, 130=Aborted",
        )
        out = capsys.readouterr().out
        for section in [
            "What",
            "Usage",
            "Parameters",
            "Options",
            "Examples",
            "Configuration",
            "Output",
            "Exit Codes",
        ]:
            assert section in out, f"Missing section: {section}"

    def test_empty_sections_omitted(self, capsys):
        cli_utils.print_help_banner(what="Only what")
        out = capsys.readouterr().out
        assert "What" in out
        assert "Usage" not in out


# -----------------------------------------------------------------------
# enable_windows_ansi() tests
# -----------------------------------------------------------------------


class TestEnableWindowsAnsi:
    """Verify that enable_windows_ansi() runs without error."""

    def test_runs_without_error(self):
        cli_utils.enable_windows_ansi()


# -----------------------------------------------------------------------
# add_no_color_arg / apply_color_from_args tests
# -----------------------------------------------------------------------


class TestNoColorArg:

    def teardown_method(self):
        cli_utils.set_use_color(True)

    def test_add_no_color_arg(self):
        import argparse

        parser = argparse.ArgumentParser()
        cli_utils.add_no_color_arg(parser)
        args = parser.parse_args(["--no-color"])
        assert args.no_color is True

    def test_apply_disables_color(self):
        import argparse

        parser = argparse.ArgumentParser()
        cli_utils.add_no_color_arg(parser)
        args = parser.parse_args(["--no-color"])
        cli_utils.apply_color_from_args(args)
        assert cli_utils.get_use_color() is False
