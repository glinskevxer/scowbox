"""``scowbox shift`` — the dredge tender's log."""

from __future__ import annotations

import datetime as dt

import click

from scowbox.model.plant import Dredge, Plant
from scowbox.model.shift import Downtime, Reason, Shift
from scowbox.pay.timeloss import credited_days, standby_days, tally
from scowbox.store import shifts
from scowbox.store.book import book
from scowbox.units.clock import moment


@click.group()
def shift() -> None:
    """Dredges and the shifts they work."""


@shift.command("dredge")
@click.argument("ident")
@click.argument("name")
@click.option(
    "--plant",
    type=click.Choice([p.value for p in Plant]),
    required=True,
    help="What kind of dredge it is.",
)
@click.option("--operator", required=True, help="Who works it.")
@click.pass_context
def add_dredge(ctx: click.Context, ident: str, name: str, plant: str, operator: str) -> None:
    """Put a dredge in the book."""
    record = Dredge(ident, name, Plant(plant), operator)
    with book(ctx.obj["book"]) as connection:
        shifts.add_dredge(connection, record)
    click.echo(record.describe())


@shift.command("log")
@click.argument("ident")
@click.option("--dredge", required=True, help="The dredge that worked it.")
@click.option("--reach", required=True, help="The reach it worked.")
@click.option("--on", "day", type=click.DateTime(["%Y-%m-%d"]), required=True)
@click.option("--from", "began", required=True, help="Start of the shift, such as 06:00.")
@click.option("--to", "ended", required=True, help="End of the shift, such as 18:00.")
@click.pass_context
def log_shift(
    ctx: click.Context,
    ident: str,
    dredge: str,
    reach: str,
    day: dt.datetime,
    began: str,
    ended: str,
) -> None:
    """Log a shift."""
    record = Shift(
        ident=ident,
        dredge=dredge,
        reach=reach,
        began=moment(day.date(), began),
        ended=moment(day.date(), ended),
    )
    with book(ctx.obj["book"]) as connection:
        shifts.add(connection, record)
    click.echo(f"{record.ident} {record.dredge} on {record.reach}, {record.gross_hours:g} hours")


@shift.command("stop")
@click.argument("ident")
@click.option("--from", "began", required=True, help="Start of the interruption.")
@click.option("--to", "ended", required=True, help="End of the interruption.")
@click.option(
    "--reason",
    type=click.Choice([r.value for r in Reason]),
    required=True,
    help="Why work stopped.",
)
@click.option("--note", default="", help="Anything the tender wrote down.")
@click.pass_context
def stop_shift(
    ctx: click.Context, ident: str, began: str, ended: str, reason: str, note: str
) -> None:
    """Add an interruption to a shift already logged."""
    with book(ctx.obj["book"]) as connection:
        held = shifts.get(connection, ident)
        interruption = Downtime(
            moment(held.day, began), moment(held.day, ended), Reason(reason), note
        )
        shifts.stop(connection, ident, interruption)
    click.echo(
        f"{ident}  {interruption.hours:g} hours {interruption.reason.value}"
        f"  {'allowable' if interruption.reason.allowable else 'contractor'}"
    )


@shift.command("list")
@click.option("--reach", default=None, help="Only shifts on this reach.")
@click.pass_context
def list_shifts(ctx: click.Context, reach: str | None) -> None:
    """Shifts in the book, oldest first."""
    with book(ctx.obj["book"]) as connection:
        found = shifts.for_reach(connection, reach) if reach else shifts.listed(connection)
    if not found:
        click.echo("no shifts")
        return
    for record in found:
        click.echo(
            f"{record.ident}  {record.day}  {record.dredge}  {record.reach}"
            f"  {record.gross_hours:>5.1f} gross  {record.effective_hours:>5.1f} effective"
        )


@shift.command("time")
@click.option("--from", "first", type=click.DateTime(["%Y-%m-%d"]), required=True)
@click.option("--to", "last", type=click.DateTime(["%Y-%m-%d"]), required=True)
@click.option("--share", type=float, default=0.5, show_default=True, help="Day credit share.")
@click.pass_context
def shift_time(ctx: click.Context, first: dt.datetime, last: dt.datetime, share: float) -> None:
    """Add the shifts up and sort the downtime three ways."""
    with book(ctx.obj["book"]) as connection:
        found = shifts.between(connection, first.date(), last.date())
    got = tally(found)
    click.echo(f"shifts       {got.shifts:,}")
    click.echo(f"gross        {got.gross_hours:,.2f} hours")
    click.echo(f"effective    {got.effective_hours:,.2f} hours ({got.share_effective:.1%})")
    click.echo(f"downtime     {got.down_hours:,.2f} hours")
    click.echo(f"  allowable  {got.allowable_hours:,.2f} hours")
    click.echo(f"  standby    {got.standby_hours:,.2f} hours")
    click.echo(f"  contractor {got.contractor_hours:,.2f} hours")
    for reason, hours in got.by_reason:
        click.echo(f"    {reason.value:<20}{hours:>8,.2f}")
    credited = credited_days(found, share=share)
    click.echo(f"days earned  {len(credited)}")
    for day in credited:
        click.echo(f"    {day}")
    click.echo(f"standby days {standby_days(found):,.2f}")
