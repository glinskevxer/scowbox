"""Entry point for the ``scowbox`` command."""

from __future__ import annotations

import sys

import click

from scowbox import __version__
from scowbox.cli.contract import contract
from scowbox.cli.estimate import estimate
from scowbox.cli.placement import placement
from scowbox.cli.quantity import quantity
from scowbox.cli.reach import reach
from scowbox.cli.scow import scow, trip
from scowbox.cli.shift import shift
from scowbox.cli.survey import survey
from scowbox.cli.template import template
from scowbox.cli.tide import tide
from scowbox.cli.window import window
from scowbox.errors import ScowboxError, code_of
from scowbox.store.book import book, counts


@click.group()
@click.version_option(__version__, prog_name="scowbox")
@click.option(
    "--book",
    type=click.Path(dir_okay=False, path_type=str),
    default="scowbox.sqlite3",
    show_default=True,
    help="Path to the project book.",
)
@click.pass_context
def cli(ctx: click.Context, book: str) -> None:
    """Measurement and payment for a maintenance dredging contract."""
    ctx.ensure_object(dict)
    ctx.obj["book"] = book


@cli.command()
def about() -> None:
    """What this program is for."""
    click.echo(f"scowbox {__version__}")
    click.echo("Measurement and payment for a maintenance dredging contract.")
    click.echo("Surveys and scow box measure in, pay quantities and estimates out.")


@cli.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """Make a project book, or bring an existing one up to date."""
    where = ctx.obj["book"]
    with book(where, create=True):
        pass
    click.echo(f"book at {where}")


@cli.command("counts")
@click.pass_context
def show_counts(ctx: click.Context) -> None:
    """How many rows the book holds, table by table."""
    with book(ctx.obj["book"]) as connection:
        for name, number in sorted(counts(connection).items()):
            click.echo(f"{name:<16}{number:>8,}")


cli.add_command(template)
cli.add_command(reach)
cli.add_command(survey)
cli.add_command(tide)
cli.add_command(placement)
cli.add_command(scow)
cli.add_command(trip)
cli.add_command(shift)
cli.add_command(quantity)
cli.add_command(contract)
cli.add_command(estimate)
cli.add_command(window)


def run() -> int:
    """Console script wrapper that turns a domain error into a message."""
    try:
        cli.main(standalone_mode=False, obj={})
    except ScowboxError as error:
        click.echo(f"{code_of(error)}: {error}", err=True)
        return 2
    except click.ClickException as error:
        error.show()
        return error.exit_code
    except click.exceptions.Abort:
        click.echo("aborted", err=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run())
