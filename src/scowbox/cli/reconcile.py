"""``scowbox reconcile`` — settling a reach the tolerance could not."""

from __future__ import annotations

import datetime as dt

import click

from scowbox.boxmeasure.bulking import typical
from scowbox.job.quantities import determine_reach
from scowbox.model.reconciliation import Accepted, Reconciliation
from scowbox.store import reconciliations
from scowbox.store.book import book
from scowbox.units.volume import Yards


@click.group()
def reconcile() -> None:
    """Disagreements between the two measurements, and how they were settled."""


@reconcile.command("open")
@click.pass_context
def open_reaches(ctx: click.Context) -> None:
    """Reaches whose two measurements disagree and are not settled."""
    with book(ctx.obj["book"]) as connection:
        from scowbox.store import reaches as reach_store

        found = []
        for reach in reach_store.listed(connection):
            try:
                held = determine_reach(connection, reach.ident, typical("silt"))
            except Exception:  # noqa: BLE001
                continue
            if held.reconcile:
                found.append(held)
    if not found:
        click.echo("nothing outstanding")
        return
    for held in found:
        click.echo(
            f"{held.reach}  survey {held.survey.rounded() if held.survey else '-'}"
            f"  scow {held.scow.rounded() if held.scow else '-'}"
            f"  spread {held.spread:.1%}"
            if held.spread is not None
            else held.reach
        )


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
    with book(ctx.obj["book"]) as connection:
        if over:
            reconciliations.replace(connection, record)
        else:
            reconciliations.add(connection, record)
    click.echo(record.describe())


@reconcile.command("list")
@click.pass_context
def list_settlements(ctx: click.Context) -> None:
    """Every reconciliation in the book."""
    with book(ctx.obj["book"]) as connection:
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
    with book(ctx.obj["book"]) as connection:
        reconciliations.remove(connection, reach)
    click.echo(f"{reach} is back in dispute")
