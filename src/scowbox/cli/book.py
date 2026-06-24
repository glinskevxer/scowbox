"""``scowbox book`` — looking after the file itself."""

from __future__ import annotations

import click

from scowbox.cli.context import opened
from scowbox.laws import LAWS
from scowbox.store.book import counts
from scowbox.store.care import backup, compact, health
from scowbox.store.migrations import latest


@click.group()
def book() -> None:
    """The project book itself: its health, its size and its copies."""


@book.command("verify")
@click.pass_context
def verify(ctx: click.Context) -> None:
    """Ask sqlite and the schema whether anything is wrong."""
    with opened(ctx) as connection:
        found = health(connection)
    click.echo(f"schema     version {found.version} of {latest()}")
    click.echo(f"integrity  {found.integrity}")
    click.echo(f"tables     {found.tables}")
    click.echo(f"size       {found.bytes_used:,} bytes in {found.pages:,} pages")
    for orphan in found.orphans:
        click.echo(f"orphan     {orphan}")
    click.echo("sound" if found.sound else "NOT SOUND")
    if not found.sound:
        raise SystemExit(1)


@book.command("counts")
@click.pass_context
def show_counts(ctx: click.Context) -> None:
    """How many rows the book holds, table by table."""
    with opened(ctx) as connection:
        held = counts(connection)
    for name, number in sorted(held.items()):
        click.echo(f"{name:<20}{number:>10,}")
    click.echo(f"{'total':<20}{sum(held.values()):>10,}")


@book.command("backup")
@click.argument("where", type=click.Path(dir_okay=False))
@click.pass_context
def take_backup(ctx: click.Context, where: str) -> None:
    """Copy the book somewhere else without overwriting anything."""
    with opened(ctx) as connection:
        made = backup(connection, where)
    click.echo(f"copied to {made}")


@book.command("compact")
@click.pass_context
def compact_book(ctx: click.Context) -> None:
    """Vacuum the book and report what it gave back."""
    with opened(ctx) as connection:
        given = compact(connection)
    if given < 0:
        click.echo(f"{-given:,} bytes taken; the book was too small to gain by it")
        return
    click.echo(f"{given:,} bytes recovered")


@book.command("laws")
@click.option("--where", is_flag=True, help="Print the module each rule lives in.")
def laws(where: bool) -> None:
    """The standing rules this program holds a book to."""
    for law in LAWS:
        click.echo(law.line())
        if where:
            click.echo(f"{'':<14}{law.where}")
