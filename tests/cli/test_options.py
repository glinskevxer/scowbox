"""The template options are one list, and every command that takes them agrees."""

from __future__ import annotations

import click
from click.testing import CliRunner

from scowbox.cli.options import (
    DEDUCTION,
    MATERIAL,
    TEMPLATE_OPTIONS,
    bulking_of,
    template_of,
    template_options,
)
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


def test_the_material_option_hangs_on_a_command() -> None:
    @click.command()
    @MATERIAL
    def sample(material: str) -> None:
        click.echo(material)

    assert CliRunner().invoke(sample, []).output.strip() == "silt"
    assert CliRunner().invoke(sample, ["--material", "clay"]).output.strip() == "clay"


def test_the_material_option_refuses_a_material_nobody_has_a_factor_for() -> None:
    @click.command()
    @MATERIAL
    def sample(material: str) -> None:
        click.echo(material)

    assert CliRunner().invoke(sample, ["--material", "shell hash"]).exit_code != 0


def test_the_deduction_option_defaults_to_nothing() -> None:
    @click.command()
    @DEDUCTION
    def sample(deduction: float) -> None:
        click.echo(str(deduction))

    assert CliRunner().invoke(sample, []).output.strip() == "0.0"


def test_a_material_name_stands_for_its_factor() -> None:
    assert bulking_of("silt").factor == 1.20
    assert bulking_of("clay").factor > bulking_of("sand").factor
