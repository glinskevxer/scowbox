"""``scowbox book`` — looking after the file itself."""

from __future__ import annotations

import click

from scowbox.store.book import book as open_book
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
    with open_book(ctx.obj["book"]) as connection:
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
    with open_book(ctx.obj["book"]) as connection:
        held = counts(connection)
    for name, number in sorted(held.items()):
        click.echo(f"{name:<20}{number:>10,}")
    click.echo(f"{'total':<20}{sum(held.values()):>10,}")


@book.command("backup")
@click.argument("where", type=click.Path(dir_okay=False))
@click.pass_context
def take_backup(ctx: click.Context, where: str) -> None:
    """Copy the book somewhere else without overwriting anything."""
    with open_book(ctx.obj["book"]) as connection:
        made = backup(connection, where)
    click.echo(f"copied to {made}")


@book.command("compact")
@click.pass_context
def compact_book(ctx: click.Context) -> None:
    """Vacuum the book and report what it gave back."""
    with open_book(ctx.obj["book"]) as connection:
        given = compact(connection)
    if given < 0:
        click.echo(f"{-given:,} bytes taken; the book was too small to gain by it")
        return
    click.echo(f"{given:,} bytes recovered")
