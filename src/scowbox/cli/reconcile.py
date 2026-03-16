"""``scowbox reconcile`` — settling a reach the tolerance could not."""

from __future__ import annotations

import datetime as dt

import click

from scowbox.boxmeasure.bulking import materials, typical
from scowbox.cli.context import opened
from scowbox.job.quantities import determined
from scowbox.measure.governing import Determination
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
@click.option(
    "--material",
    type=click.Choice(materials()),
    default="silt",
    show_default=True,
    help="Material class, which sets the bulking factor.",
)
@click.pass_context
def open_reaches(ctx: click.Context, material: str) -> None:
    """Reaches whose two measurements disagree and are not settled."""
    found = []
    with opened(ctx) as connection:
        for reach in reaches.listed(connection):
            held = determined(connection, reach.ident, typical(material))
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
