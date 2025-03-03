"""The book.

One sqlite file holds a project: its reaches, its surveys, its scow trips, its
shift logs and its estimates. Nothing outside this package opens a connection
and nothing outside this package writes SQL.
"""
