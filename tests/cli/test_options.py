"""The template options are one list, and every command that takes them agrees."""

from __future__ import annotations

import click
from click.testing import CliRunner

from scowbox.cli.options import TEMPLATE_OPTIONS, template_of, template_options
from scowbox.units.depth import Depth


def test_the_helper_builds_the_three_depths() -> None:
    built = template_of(400, 42, 3, 2, 2)
    assert built.required_depth == Depth.of_feet(44)
    assert built.pay_depth == Depth.of_feet(46)


def test_the_options_hang_on_a_command_in_order() -> None:
    @click.command()
    @template_options
    def sample(bottom: float, depth: float, slope: float, advance: float, overdepth: float) -> None:
        click.echo(f"{bottom} {depth} {slope} {advance} {overdepth}")

    result = CliRunner().invoke(sample, ["--bottom", "400", "--depth", "42"])
    assert result.output.strip() == "400.0 42.0 3.0 0.0 0.0"


def test_every_template_option_is_hung_exactly_once() -> None:
    @click.command()
    @template_options
    def sample(**_: object) -> None:
        pass

    names = [p.name for p in sample.params]
    assert names == ["bottom", "depth", "slope", "advance", "overdepth"]
    assert len(names) == len(TEMPLATE_OPTIONS)
