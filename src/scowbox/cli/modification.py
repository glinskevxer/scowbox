"""``scowbox modification`` — the signed changes to the contract."""

from __future__ import annotations

import datetime as dt

import click

from scowbox.cli.context import opened
from scowbox.job.contract import as_modified
from scowbox.model.modification import Change, Modification
from scowbox.store import contracts, modifications
from scowbox.units.money import Money


@click.group()
def modification() -> None:
    """Signed modifications and what they change."""


@modification.command("add")
@click.argument("number")
@click.option("--on", "day", type=click.DateTime(["%Y-%m-%d"]), required=True, help="Day signed.")
@click.option(
    "--change",
    type=click.Choice([c.value for c in Change]),
    required=True,
    help="What the modification changes.",
)
@click.option("--description", required=True, help="What it did.")
@click.option("--days", type=int, default=0, help="Days added, on a time extension.")
@click.option("--item", default="", help="Line item, on a price or a new item.")
@click.option("--price", default=None, help="Unit price, on a price or a new item.")
@click.pass_context
def add_modification(
    ctx: click.Context,
    number: str,
    day: dt.datetime,
    change: str,
    description: str,
    days: int,
    item: str,
    price: str | None,
) -> None:
    """Put a signed modification in the book."""
    record = Modification(
        number=number,
        signed_on=day.date(),
        change=Change(change),
        description=description,
        days=days,
        item=item,
        price=None if price is None else Money.parse(price),
    )
    with opened(ctx) as connection:
        held = contracts.only(connection)
        modifications.add(connection, held.number, record)
    click.echo(record.describe())


@modification.command("list")
@click.pass_context
def list_modifications(ctx: click.Context) -> None:
    """Every modification on the contract, oldest first."""
    with opened(ctx) as connection:
        held = contracts.only(connection)
        found = modifications.listed(connection, held.number)
    if not found:
        click.echo("no modifications")
        return
    for record in found:
        click.echo(record.describe())
        click.echo(f"  {record.description}")


@modification.command("current")
@click.pass_context
def current_contract(ctx: click.Context) -> None:
    """The contract as it stands with every modification applied."""
    with opened(ctx) as connection:
        found = as_modified(connection)
    contract = found.contract
    click.echo(contract.number)
    click.echo(f"  modifications {found.count}")
    click.echo(f"  time          {contract.days} days, complete {contract.completion}")
    if found.added_days:
        click.echo(f"  extended by   {found.added_days:+,} days")
    click.echo("  schedule")
    for item in contract.items:
        group = f"  {item.group}" if item.group else ""
        click.echo(
            f"    {item.ident}  {item.description[:32]:<34}"
            f"{item.unit_price!s:>16} per {item.unit.value}{group}"
        )


@modification.command("drop")
@click.argument("number")
@click.pass_context
def drop_modification(ctx: click.Context, number: str) -> None:
    """Take a modification back out of the book."""
    with opened(ctx) as connection:
        held = contracts.only(connection)
        modifications.remove(connection, held.number, number)
    click.echo(f"removed {number}")
