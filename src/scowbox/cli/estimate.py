"""``scowbox estimate`` — the monthly progress estimate."""

from __future__ import annotations

import datetime as dt

import click

from scowbox.cli.context import opened
from scowbox.cli.options import DEDUCTION, MATERIAL, bulking_of
from scowbox.job.estimating import draft, write
from scowbox.pay.estimate import Estimate
from scowbox.store import contracts, estimates


@click.group()
def estimate() -> None:
    """Progress estimates against the contract."""


def _print(found: Estimate) -> None:
    click.echo(f"{found.ident}  estimate {found.number} through {found.through}")
    click.echo(f"  {'item':<9}{'description':<32}{'to date':>14}{'this period':>14}{'earned':>16}")
    for line in found.lines:
        click.echo(
            f"  {line.item:<9}{line.description[:31]:<32}"
            f"{line.to_date:>14,.2f}{line.this_period:>14,.2f}{line.earned!s:>16}"
        )
    click.echo(f"  earned to date {found.earned!s:>24}")
    click.echo(f"  retainage      {-found.retained!s:>24}")
    if found.days_late:
        click.echo(f"  damages        {-found.liquidated!s:>24}  ({found.days_late} days)")
    click.echo(f"  payable        {found.payable!s:>24}")
    click.echo(f"  paid before    {-found.paid_before!s:>24}")
    click.echo(f"  due            {found.due!s:>24}")


@estimate.command("draft")
@click.option(
    "--through",
    type=click.DateTime(["%Y-%m-%d"]),
    required=True,
    help="Last day the estimate covers.",
)
@MATERIAL
@DEDUCTION
@click.option("--claim", multiple=True, help="A lump sum item and share, as LI-0009=1.0")
@click.option("--final", is_flag=True, help="Close the contract and release retainage.")
@click.pass_context
def draft_estimate(
    ctx: click.Context,
    through: dt.datetime,
    material: str,
    deduction: float,
    claim: tuple[str, ...],
    final: bool,
) -> None:
    """Work out the next estimate without writing it."""
    lumps = dict(_claim(one) for one in claim)
    with opened(ctx) as connection:
        drafted = draft(
            connection,
            through.date(),
            bulking_of(material),
            deduction=deduction,
            lump_sums=lumps,
            final=final,
        )
    _print(drafted.estimate)
    if drafted.days_earned:
        click.echo(f"  {drafted.days_earned} days of contract time earned back")
    for ident, reason in drafted.left_out:
        click.echo(f"  not measured: {ident}  {reason}")


@estimate.command("write")
@click.option(
    "--through",
    type=click.DateTime(["%Y-%m-%d"]),
    required=True,
    help="Last day the estimate covers.",
)
@MATERIAL
@DEDUCTION
@click.option("--claim", multiple=True, help="A lump sum item and share, as LI-0009=1.0")
@click.option("--final", is_flag=True, help="Close the contract and release retainage.")
@click.pass_context
def write_estimate(
    ctx: click.Context,
    through: dt.datetime,
    material: str,
    deduction: float,
    claim: tuple[str, ...],
    final: bool,
) -> None:
    """Work out the next estimate and put it in the book."""
    lumps = dict(_claim(one) for one in claim)
    with opened(ctx) as connection:
        drafted = draft(
            connection,
            through.date(),
            bulking_of(material),
            deduction=deduction,
            lump_sums=lumps,
            final=final,
        )
        written = write(connection, drafted)
    _print(written)


@estimate.command("list")
@click.pass_context
def list_estimates(ctx: click.Context) -> None:
    """Every estimate written on the contract."""
    with opened(ctx) as connection:
        held = contracts.only(connection)
        found = estimates.listed(connection, held.number)
    if not found:
        click.echo("no estimates")
        return
    for one in found:
        click.echo(
            f"{one.ident}  through {one.through}  earned {one.earned!s:>16}  due {one.due!s:>16}"
        )


@estimate.command("show")
@click.argument("ident")
@click.pass_context
def show_estimate(ctx: click.Context, ident: str) -> None:
    """One estimate in full."""
    with opened(ctx) as connection:
        found = estimates.get(connection, ident)
    _print(found)


def _claim(text: str) -> tuple[str, float]:
    item, _, share = text.partition("=")
    if not share:
        raise click.BadParameter(f"{text!r} is not an item and a share, such as LI-0009=1.0")
    return item.strip(), float(share)
