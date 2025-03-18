"""``scowbox template`` — what a cut looks like before anybody digs it."""

from __future__ import annotations

import click

from scowbox.cli.options import template_of, template_options
from scowbox.section.prism import Cut, Prism
from scowbox.units.depth import Elevation

DATUM = Elevation(0)


@click.group()
def template() -> None:
    """Work out the figures a template gives before any survey exists."""


@template.command()
@template_options
def depths(bottom: float, depth: float, slope: float, advance: float, overdepth: float) -> None:
    """Print the three depths a template gives."""
    cut = template_of(bottom, depth, slope, advance, overdepth)
    click.echo(f"authorized  {cut.authorized_depth}")
    click.echo(f"required    {cut.required_depth}")
    click.echo(f"pay         {cut.pay_depth}")
    click.echo(cut.describe())


@template.command()
@template_options
def area(bottom: float, depth: float, slope: float, advance: float, overdepth: float) -> None:
    """Print the cross section area of each cut, to the datum."""
    cut = template_of(bottom, depth, slope, advance, overdepth)
    for which in Cut:
        prism = Prism.of_template(cut, which)
        click.echo(
            f"{which.value:<11}{prism.area_to(DATUM):>12,.1f} sq ft"
            f"   top width {2 * prism.top_half_width(DATUM):,.1f} ft"
        )
