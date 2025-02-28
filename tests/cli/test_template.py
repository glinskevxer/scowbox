"""``scowbox template`` prints what the drawing says before anybody digs."""

from __future__ import annotations

from click.testing import CliRunner

from scowbox.cli.main import cli

BASE = ["--bottom", "400", "--depth", "42", "--slope", "3"]


def run(*args: str) -> str:
    result = CliRunner().invoke(cli, ["template", *args], obj={})
    assert result.exit_code == 0, result.output
    return result.output


def test_depths_prints_the_three_of_them() -> None:
    out = run("depths", *BASE, "--advance", "2", "--overdepth", "2")
    assert "authorized  42.00 ft" in out
    assert "required    44.00 ft" in out
    assert "pay         46.00 ft" in out


def test_depths_collapses_when_there_is_no_allowance() -> None:
    out = run("depths", *BASE)
    heads = [line.split()[1] for line in out.strip().splitlines()[:3]]
    assert heads == ["42.00", "42.00", "42.00"]


def test_area_prints_a_line_for_each_cut() -> None:
    out = run("area", *BASE, "--advance", "2", "--overdepth", "2")
    assert "authorized" in out
    assert "required" in out
    assert "pay" in out
    assert "sq ft" in out


def test_area_grows_with_the_cut() -> None:
    out = run("area", *BASE, "--advance", "2", "--overdepth", "2")
    numbers = [line.split()[1] for line in out.strip().splitlines()]
    values = [float(n.replace(",", "")) for n in numbers]
    assert values == sorted(values)


def test_a_bad_template_is_reported_not_traced() -> None:
    result = CliRunner().invoke(cli, ["template", "depths", "--bottom", "0", "--depth", "42"])
    assert result.exit_code != 0


def test_the_group_has_help_of_its_own() -> None:
    out = run("--help")
    assert "template" in out
