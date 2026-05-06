"""``scowbox quantity`` — what has been measured and what governs it."""

from __future__ import annotations

import click

from scowbox.cli.context import opened
from scowbox.cli.options import DEDUCTION, MATERIAL, bulking_of
from scowbox.job.quantities import by_group, determine_reach, unmeasured


@click.group()
def quantity() -> None:
    """Pay quantities as the book can measure them."""


@quantity.command("reach")
@click.argument("ident")
@MATERIAL
@DEDUCTION
@click.option(
    "--tolerance",
    type=float,
    default=0.10,
    show_default=True,
    help="Share the two measurements may differ by before a reach is flagged.",
)
@click.pass_context
def reach_quantity(
    ctx: click.Context, ident: str, material: str, deduction: float, tolerance: float
) -> None:
    """Measure one reach every way its method allows."""
    with opened(ctx) as connection:
        found = determine_reach(
            connection,
            ident,
            bulking_of(material),
            deduction=deduction,
            tolerance=tolerance,
        )
    click.echo(f"{found.reach}  measured by {found.method.value}")
    click.echo(f"  survey     {found.survey.rounded() if found.survey else 'not taken'}")
    click.echo(f"  scow       {found.scow.rounded() if found.scow else 'not taken'}")
    if found.spread is not None:
        click.echo(f"  spread     {found.spread:.1%}")
    click.echo(f"  governs    {found.governs.value}")
    click.echo(f"  quantity   {found.quantity.rounded()}")
    if found.reconcile:
        click.echo("  RECONCILE  the two measurements do not agree")
    for note in found.notes:
        click.echo(f"  note       {note}")


@quantity.command("groups")
@MATERIAL
@DEDUCTION
@click.pass_context
def group_quantities(ctx: click.Context, material: str, deduction: float) -> None:
    """Pay quantities gathered into the groups the bid schedule bills by."""
    with opened(ctx) as connection:
        gathered = by_group(connection, bulking_of(material), deduction=deduction)
    if not gathered:
        click.echo("nothing measured yet")
        return
    for group, yards in sorted(gathered.items()):
        click.echo(f"{group:<16}{yards.rounded():>16}")


@quantity.command("gaps")
@MATERIAL
@click.pass_context
def quantity_gaps(ctx: click.Context, material: str) -> None:
    """Reaches the book cannot measure yet, and why."""
    with opened(ctx) as connection:
        missing = unmeasured(connection, bulking_of(material))
    if not missing:
        click.echo("every reach is measured")
        return
    for ident, reason in missing:
        click.echo(f"{ident}  {reason}")
