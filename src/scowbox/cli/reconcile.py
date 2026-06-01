"""``scowbox reconcile`` — settling a reach the tolerance could not."""

from __future__ import annotations

import datetime as dt

import click

from scowbox.cli.context import opened
from scowbox.cli.options import MATERIAL, bulking_of
from scowbox.job.quantities import determined
from scowbox.measure.governing import Determination
from scowbox.measure.tolerance import sensitivity
from scowbox.model.reconciliation import Accepted, Reconciliation
from scowbox.store import reaches, reconciliations
from scowbox.units.volume import Yards


@click.group()
def reconcile() -> None:
    """Disagreements between the two measurements, and how they were settled."""


def _line(held: Determination) -> str:
    """One outstanding reach, with both readings and the gap between them."""
    survey = held.survey.rounded() if held.survey is not None else "not taken"
    scow = held.scow.rounded() if held.scow is not None else "not taken"
    spread = f"{held.spread:.1%}" if held.spread is not None else "-"
    return f"{held.reach}  survey {survey:>14}  scow {scow:>14}  spread {spread:>7}"


@reconcile.command("open")
@MATERIAL
@click.pass_context
def open_reaches(ctx: click.Context, material: str) -> None:
    """Reaches whose two measurements disagree and are not settled."""
    found = []
    with opened(ctx) as connection:
        for reach in reaches.listed(connection):
            held = determined(connection, reach.ident, bulking_of(material))
            if held is not None and held.reconcile:
                found.append(held)
    if not found:
        click.echo("nothing outstanding")
        return
    for held in found:
        click.echo(_line(held))


@reconcile.command("settle")
@click.argument("reach")
@click.option(
    "--accept",
    type=click.Choice([a.value for a in Accepted]),
    required=True,
    help="Which answer the parties settled on.",
)
@click.option("--on", "day", type=click.DateTime(["%Y-%m-%d"]), required=True, help="Day settled.")
@click.option("--by", "decided_by", required=True, help="Who decided it.")
@click.option("--quantity", type=float, default=None, help="Agreed figure in cubic yards.")
@click.option("--note", default="", help="What it was agreed on.")
@click.option("--replace", "over", is_flag=True, help="Overwrite a settlement already there.")
@click.pass_context
def settle(
    ctx: click.Context,
    reach: str,
    accept: str,
    day: dt.datetime,
    decided_by: str,
    quantity: float | None,
    note: str,
    over: bool,
) -> None:
    """Record what the parties agreed for one reach."""
    record = Reconciliation(
        reach=reach,
        decided_on=day.date(),
        accepted=Accepted(accept),
        decided_by=decided_by,
        note=note,
        quantity=None if quantity is None else Yards.of_yards(quantity),
    )
    with opened(ctx) as connection:
        if over:
            reconciliations.replace(connection, record)
        else:
            reconciliations.add(connection, record)
    click.echo(record.describe())


@reconcile.command("list")
@click.pass_context
def list_settlements(ctx: click.Context) -> None:
    """Every reconciliation in the book."""
    with opened(ctx) as connection:
        found = reconciliations.listed(connection)
    if not found:
        click.echo("no reconciliations")
        return
    for record in found:
        click.echo(record.describe())
        if record.note.strip():
            click.echo(f"  {record.note}")


@reconcile.command("drop")
@click.argument("reach")
@click.pass_context
def drop(ctx: click.Context, reach: str) -> None:
    """Take a reconciliation back out, which puts the reach back in dispute."""
    with opened(ctx) as connection:
        reconciliations.remove(connection, reach)
    click.echo(f"{reach} is back in dispute")


@reconcile.command("explain")
@click.argument("reach")
@MATERIAL
@click.pass_context
def explain(ctx: click.Context, reach: str, material: str) -> None:
    """What would have to move for a reach to agree with itself."""
    with opened(ctx) as connection:
        held = determined(connection, reach, bulking_of(material))
        if held is None:
            raise click.ClickException(f"{reach} cannot be measured yet")
        found = sensitivity(held, bulking_of(material))
    click.echo(found.describe())
    click.echo(f"  difference   {found.difference.rounded()}")
    click.echo(f"  tolerance    {found.spread:.1%} would admit this pair")
    factor = found.factor
    if factor is None:
        click.echo("  bulking      nothing to solve for, one side measured nothing")
    else:
        credible = "inside" if found.credible else "outside"
        click.echo(f"  bulking      {factor:.3f} would match, {credible} the usual range")
    deduction = found.deduction
    if deduction is None:
        click.echo("  deduction    cannot close this gap, the scows are already the lesser")
    else:
        click.echo(f"  deduction    {deduction:.1%} would bring the scows to the survey")
