"""``scowbox scow`` and ``scowbox trip`` — the mechanical dredge's records."""

from __future__ import annotations

import datetime as dt

import click

from scowbox.boxmeasure.box import measure
from scowbox.errors import MissingError
from scowbox.model.placement import Grade, PlacementTicket
from scowbox.model.scow import BoxReading, Corner, Scow, ScowTrip
from scowbox.store import scows, trips
from scowbox.store.book import book
from scowbox.units.clock import moment

CORNERS = {
    "pb": Corner.PORT_BOW,
    "sb": Corner.STARBOARD_BOW,
    "ps": Corner.PORT_STERN,
    "ss": Corner.STARBOARD_STERN,
}


@click.group()
def scow() -> None:
    """The scow fleet."""


@scow.command("add")
@click.argument("ident")
@click.argument("name")
@click.option("--length", type=float, required=True, help="Inside length in feet.")
@click.option("--width", type=float, required=True, help="Inside width in feet.")
@click.option("--depth", type=float, required=True, help="Inside depth in feet.")
@click.pass_context
def add_scow(
    ctx: click.Context, ident: str, name: str, length: float, width: float, depth: float
) -> None:
    """Put a scow in the book."""
    record = Scow(ident, name, length, width, depth)
    with book(ctx.obj["book"]) as connection:
        scows.add(connection, record)
    click.echo(record.describe())


@scow.command("list")
@click.pass_context
def list_scows(ctx: click.Context) -> None:
    """Every scow in the fleet."""
    with book(ctx.obj["book"]) as connection:
        found = scows.listed(connection)
    if not found:
        click.echo("no scows")
        return
    for record in found:
        click.echo(f"{record.describe()}   {record.box_area:,.0f} sq ft")


@click.group()
def trip() -> None:
    """Scow loads, their box measures and their tickets."""


@trip.command("add")
@click.argument("ident")
@click.option("--scow", "scow_ident", required=True, help="The scow that carried it.")
@click.option("--reach", required=True, help="The reach it came out of.")
@click.option("--on", "loaded_on", type=click.DateTime(["%Y-%m-%d"]), required=True)
@click.option("--to", "placement", required=True, help="Where it is bound.")
@click.pass_context
def add_trip(
    ctx: click.Context,
    ident: str,
    scow_ident: str,
    reach: str,
    loaded_on: dt.datetime,
    placement: str,
) -> None:
    """Log a scow load."""
    record = ScowTrip(
        ident=ident,
        scow=scow_ident,
        reach=reach,
        loaded_on=loaded_on.date(),
        placement=placement,
    )
    with book(ctx.obj["book"]) as connection:
        trips.add(connection, record)
    click.echo(f"{record.ident} {record.scow} out of {record.reach} for {record.placement}")


@trip.command("measure")
@click.argument("ident")
@click.option("--light", type=float, required=True, help="Light reading at every corner.")
@click.option("--pb", type=float, required=True, help="Loaded reading, port bow.")
@click.option("--sb", type=float, required=True, help="Loaded reading, starboard bow.")
@click.option("--ps", type=float, required=True, help="Loaded reading, port stern.")
@click.option("--ss", type=float, required=True, help="Loaded reading, starboard stern.")
@click.pass_context
def measure_trip(
    ctx: click.Context, ident: str, light: float, pb: float, sb: float, ps: float, ss: float
) -> None:
    """Take a box measure on a trip."""
    loaded = {"pb": pb, "sb": sb, "ps": ps, "ss": ss}
    readings = tuple(BoxReading(corner, light, loaded[key]) for key, corner in CORNERS.items())
    with book(ctx.obj["book"]) as connection:
        trips.measure(connection, ident, readings)
        held = trips.get(connection, ident)
        got = measure(scows.get(connection, held.scow), held)
    click.echo(f"{ident}  mean {got.mean_material:.2f} ft  {got.scow_yards}")
    click.echo(f"  trim {got.trim:+.2f} ft   heel {got.heel:+.2f} ft")
    for note in got.suspect:
        click.echo(f"  suspect: {note}")


@trip.command("release")
@click.argument("ident")
@click.option("--at", "area", required=True, help="Where it was released.")
@click.option("--on", "day", type=click.DateTime(["%Y-%m-%d"]), required=True)
@click.option("--time", "clock", required=True, help="Time of release, such as 11:20.")
@click.option(
    "--grade",
    type=click.Choice([g.value for g in Grade]),
    required=True,
    help="What the sediment testing found.",
)
@click.pass_context
def release_trip(
    ctx: click.Context, ident: str, area: str, day: dt.datetime, clock: str, grade: str
) -> None:
    """Write the placement ticket that closes a trip out."""
    with book(ctx.obj["book"]) as connection:
        held = trips.get(connection, ident)
        got = measure(scows.get(connection, held.scow), held)
        ticket = PlacementTicket(
            trip=ident,
            area=area,
            released=moment(day.date(), clock),
            yards=got.scow_yards,
            grade=Grade(grade),
        )
        trips.release(connection, ticket)
    click.echo(f"{ident} released at {area}, {ticket.yards}")


@trip.command("list")
@click.option("--reach", default=None, help="Only trips out of this reach.")
@click.pass_context
def list_trips(ctx: click.Context, reach: str | None) -> None:
    """Trips in the book, oldest first."""
    with book(ctx.obj["book"]) as connection:
        found = trips.for_reach(connection, reach) if reach else trips.listed(connection)
        waiting = set(trips.untick(connection))
    if not found:
        click.echo("no trips")
        return
    for record in found:
        state = "no ticket" if record.ident in waiting else "released"
        box = "measured" if record.measured else "unmeasured"
        click.echo(
            f"{record.ident}  {record.loaded_on}  {record.scow}  {record.reach}  {box:<10} {state}"
        )


@trip.command("open")
@click.pass_context
def open_trips(ctx: click.Context) -> None:
    """Trips that left with no placement ticket against them."""
    with book(ctx.obj["book"]) as connection:
        waiting = trips.untick(connection)
    if not waiting:
        click.echo("every trip is ticketed")
        return
    for ident in waiting:
        click.echo(ident)


@trip.command("show")
@click.argument("ident")
@click.pass_context
def show_trip(ctx: click.Context, ident: str) -> None:
    """One trip, its box measure and its ticket."""
    with book(ctx.obj["book"]) as connection:
        held = trips.get(connection, ident)
        fleet = scows.get(connection, held.scow)
        got = measure(fleet, held) if held.measured else None
        try:
            ticket = trips.ticket_of(connection, ident)
        except MissingError:
            ticket = None
    click.echo(f"{held.ident}  {held.loaded_on}")
    click.echo(f"  scow       {fleet.describe()}")
    click.echo(f"  reach      {held.reach}")
    click.echo(f"  bound for  {held.placement}")
    if got is None:
        click.echo("  box        not measured")
    else:
        click.echo(f"  box        mean {got.mean_material:.2f} ft, {got.scow_yards}")
        click.echo(f"  attitude   trim {got.trim:+.2f} ft, heel {got.heel:+.2f} ft")
    if ticket is None:
        click.echo("  ticket     none")
    else:
        click.echo(f"  ticket     {ticket.area} at {ticket.released:%Y-%m-%d %H:%M}")
