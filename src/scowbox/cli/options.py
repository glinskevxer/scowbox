"""Options more than one command takes.

The five template options were written out twice, once on ``template`` and once
on ``reach add``, and the two copies had already drifted: one defaulted the side
slope to three and the other made it required. A template read one way by one
command and another way by the other is the sort of disagreement that surfaces
as an estimate that will not tie to a drawing.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

import click

from scowbox.boxmeasure.bulking import Bulking, materials, typical
from scowbox.model.channel import Template
from scowbox.units.depth import Depth

Decorated = TypeVar("Decorated", bound=Callable[..., Any])

TEMPLATE_OPTIONS: list[Callable[[Decorated], Decorated]] = [
    click.option("--bottom", type=float, required=True, help="Bottom width in feet."),
    click.option("--depth", type=float, required=True, help="Authorized depth in feet."),
    click.option("--slope", type=float, default=3.0, show_default=True, help="Side slope H:1."),
    click.option("--advance", type=float, default=0.0, show_default=True, help="Advance feet."),
    click.option("--overdepth", type=float, default=0.0, show_default=True, help="Paid feet."),
]


def template_options(command: Decorated) -> Decorated:
    """Hang the five template options on a command, in a fixed order."""
    for option in reversed(TEMPLATE_OPTIONS):
        command = option(command)
    return command


def template_of(
    bottom: float, depth: float, slope: float, advance: float, overdepth: float
) -> Template:
    """Build a template from the five options, so every command builds it alike."""
    return Template(
        bottom_width=bottom,
        authorized_depth=Depth.of_feet(depth),
        side_slope=slope,
        advance_maintenance=advance,
        overdepth=overdepth,
    )


MATERIAL = click.option(
    "--material",
    type=click.Choice(materials()),
    default="silt",
    show_default=True,
    help="Material class, which sets the bulking factor.",
)
"""Written out five times before this, and two of the five had drifted onto a
different default, so the same book answered two different quantities depending
on which command you asked."""

DEDUCTION = click.option(
    "--deduction",
    type=float,
    default=0.0,
    show_default=True,
    help="Share of a scow quantity that falls outside the prism.",
)


def bulking_of(material: str) -> Bulking:
    """The factor a material name stands for."""
    return typical(material)
