"""Entry point for the ``scowbox`` command."""

from __future__ import annotations

import sys

import click

from scowbox import __version__
from scowbox.cli.template import template
from scowbox.errors import ScowboxError, code_of


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


cli.add_command(template)


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
