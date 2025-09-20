"""``scowbox contract`` — the bid schedule and the terms."""

from __future__ import annotations

import datetime as dt

import click

from scowbox.model.contract import Contract, LineItem, Unit
from scowbox.store import contracts
from scowbox.store.book import book
from scowbox.units.money import Money


@click.group()
def contract() -> None:
    """The contract the estimates are written against."""


@contract.command("add")
@click.argument("number")
@click.option("--awarded", type=click.DateTime(["%Y-%m-%d"]), required=True, help="Day of award.")
@click.option(
    "--ntp",
    type=click.DateTime(["%Y-%m-%d"]),
    required=True,
    help="Day of the notice to proceed.",
)
@click.option("--days", type=int, required=True, help="Contract time in calendar days.")
@click.option(
    "--retainage",
    type=float,
    default=0.05,
    show_default=True,
    help="Share of the earned amount withheld.",
)
@click.option("--liquidated", default="$0.00", show_default=True, help="Damages per day.")
@click.pass_context
def add_contract(
    ctx: click.Context,
    number: str,
    awarded: dt.datetime,
    ntp: dt.datetime,
    days: int,
    retainage: float,
    liquidated: str,
) -> None:
    """Put a contract in the book, with no line items yet."""
    record = Contract(
        number=number,
        awarded=awarded.date(),
        notice_to_proceed=ntp.date(),
        days=days,
        retainage=retainage,
        liquidated=Money.parse(liquidated),
    )
    with book(ctx.obj["book"]) as connection:
        contracts.add(connection, record)
    click.echo(f"{record.number}, {record.days} days, complete {record.completion}")


@contract.command("item")
@click.argument("ident")
@click.argument("description")
@click.option(
    "--unit",
    type=click.Choice([u.value for u in Unit]),
    required=True,
    help="What the item is priced by.",
)
@click.option("--price", required=True, help="Unit price, such as $7.35.")
@click.option("--group", default="", help="Pay group, on a cubic yard item.")
@click.option("--estimated", type=float, default=0.0, help="Bid quantity.")
@click.pass_context
def add_item(
    ctx: click.Context,
    ident: str,
    description: str,
    unit: str,
    price: str,
    group: str,
    estimated: float,
) -> None:
    """Add one line to the bid schedule."""
    item = LineItem(
        ident=ident,
        description=description,
        unit=Unit(unit),
        unit_price=Money.parse(price),
        group=group,
        estimated=estimated,
    )
    with book(ctx.obj["book"]) as connection:
        held = contracts.only(connection)
        contracts.add_item(connection, held.number, item)
    click.echo(f"{item.ident} {item.description} at {item.unit_price} per {item.unit.value}")


@contract.command("show")
@click.pass_context
def show_contract(ctx: click.Context) -> None:
    """The contract and its whole bid schedule."""
    with book(ctx.obj["book"]) as connection:
        held = contracts.only(connection)
    click.echo(held.number)
    click.echo(f"  awarded    {held.awarded}")
    click.echo(f"  proceed    {held.notice_to_proceed}")
    click.echo(f"  time       {held.days} days, complete {held.completion}")
    click.echo(f"  retainage  {held.retainage:.1%}")
    click.echo(f"  damages    {held.liquidated} per day")
    click.echo("  schedule")
    for item in held.items:
        group = f"  {item.group}" if item.group else ""
        click.echo(
            f"    {item.ident}  {item.description:<34} {item.unit_price!s:>16}"
            f" per {item.unit.value}{group}"
        )
