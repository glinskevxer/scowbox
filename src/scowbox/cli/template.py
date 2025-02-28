"""``scowbox template`` — what a cut looks like before anybody digs it."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

import click

from scowbox.model.channel import Template
from scowbox.section.prism import Cut, Prism
from scowbox.units.depth import Depth, Elevation

DATUM = Elevation(0)


@click.group()
def template() -> None:
    """Work out the figures a template gives before any survey exists."""


def _template(
    bottom: float, depth: float, slope: float, advance: float, overdepth: float
) -> Template:
    return Template(
        bottom_width=bottom,
        authorized_depth=Depth.of_feet(depth),
        side_slope=slope,
        advance_maintenance=advance,
        overdepth=overdepth,
    )


Decorated = TypeVar("Decorated", bound=Callable[..., Any])

_OPTIONS: list[Callable[[Decorated], Decorated]] = [
    click.option("--bottom", type=float, required=True, help="Bottom width in feet."),
    click.option("--depth", type=float, required=True, help="Authorized depth in feet."),
    click.option("--slope", type=float, default=3.0, show_default=True, help="Side slope H:1."),
    click.option("--advance", type=float, default=0.0, show_default=True, help="Advance feet."),
    click.option("--overdepth", type=float, default=0.0, show_default=True, help="Paid feet."),
]


def _with_options(command: Decorated) -> Decorated:
    """Hang the five template options on a command.

    Both subcommands take exactly the same five, and a template read one way by
    one of them and another way by the other is the sort of thing nobody finds
    until an estimate disagrees with a drawing.
    """
    for option in reversed(_OPTIONS):
        command = option(command)
    return command


@template.command()
@_with_options
def depths(bottom: float, depth: float, slope: float, advance: float, overdepth: float) -> None:
    """Print the three depths a template gives."""
    cut = _template(bottom, depth, slope, advance, overdepth)
    click.echo(f"authorized  {cut.authorized_depth}")
    click.echo(f"required    {cut.required_depth}")
    click.echo(f"pay         {cut.pay_depth}")
    click.echo(cut.describe())


@template.command()
@_with_options
def area(bottom: float, depth: float, slope: float, advance: float, overdepth: float) -> None:
    """Print the cross section area of each cut, to the datum."""
    cut = _template(bottom, depth, slope, advance, overdepth)
    for which in Cut:
        prism = Prism.of_template(cut, which)
        click.echo(
            f"{which.value:<11}{prism.area_to(DATUM):>12,.1f} sq ft"
            f"   top width {2 * prism.top_half_width(DATUM):,.1f} ft"
        )
