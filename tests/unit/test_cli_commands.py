"""Unit tests for RAVEN CLI commands."""

from typer.testing import CliRunner
from raven.cli import app

runner = CliRunner()


def test_cli_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "RAVEN version" in result.output


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "RAVEN - Terminal AI Coding Agent" in result.output
    assert "doctor" in result.output
    assert "models" in result.output
    assert "config" in result.output


def test_cli_doctor():
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "RAVEN Diagnostic Health Check" in result.output
    assert "Python Version" in result.output


def test_cli_models():
    result = runner.invoke(app, ["models"])
    assert result.exit_code == 0
    assert "Supported Providers and Models" in result.output
    assert "openai" in result.output
    assert "anthropic" in result.output
    assert "gemini" in result.output


def test_cli_config():
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    assert "Active Configuration" in result.output
    assert "Project Root" in result.output
