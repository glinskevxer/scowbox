# Design

Why the package is shaped the way it is. Written by hand, unlike the other
three documents here, and checked by `scowbox.tools.check_design`: every module
and name it mentions in backticks has to exist.

## Two measurements and a rule between them

A maintenance dredging contract is measured two ways at once and the two never
agree. `scowbox.measure.fromsurvey` works a pair of surveys up into the volume
the bed lost. `scowbox.measure.fromscow` works a stack of box measure sheets up
into the volume that came out of the water. `scowbox.measure.governing` decides
which of them the contract lets you bill, and `scowbox.model.reconciliation`
records what the parties agreed when neither could be trusted.

That last piece is the reason this is a program rather than a spreadsheet. The
tolerance, the lesser-of-the-two rule and the reconciliation are three rules
about the output of other rules, and each of them is a place a quantity can be
wrong in a way that nothing downstream would notice.

## Measures are types

`scowbox.units.depth` keeps `Depth` and `Elevation` apart, because a survey
file writes the bed at -38.6 and a drawing writes the cut at 42, and the sign
is the only thing between them. `scowbox.units.station` holds stationing in the
notation the drawings use. `scowbox.units.volume` and `scowbox.units.money` are
integers, in hundredths of a cubic yard and in whole cents, because a reach is
a sum of a few hundred sections and an estimate is a sum of a few dozen
reaches.

## The bed is a line, not a grid

`scowbox.section.bedline` is the bed across one station: a run of shots with a
straight line between each pair, and nothing at all outside them.
`scowbox.section.prism` is the design surface. `scowbox.section.area` puts them
together by exact integration rather than sampling, solving for the offsets
where two of the curves cross so that a section answers the same number
whatever spacing the survey ran to. `scowbox.section.volume` is average end
area, with the two rules that travel with it.

## The book is read in runs, not a row at a time

`scowbox.store.trips.for_reach` and `scowbox.store.shifts.for_reach` fetch
their children in one query each rather than one a parent. That started as two
queries a trip, which was four hundred round trips on a season report and is
the only performance problem this package has ever had.

## Nothing asks what day it is

Every date is a date somebody wrote down. `scowbox.tools.check_clock` enforces
that, `scowbox.tools.check_layers` enforces the import order,
`scowbox.tools.check_printing` keeps output in `scowbox.cli`, and
`scowbox.tools.check_sql` keeps values out of statements.

## The book is one file

`scowbox.store.book` opens it, `scowbox.store.migrations` versions it, and
`scowbox.store.sqlite` is the only module that knows what a connection is.
`scowbox.store.sqlite.opened` exists because a sqlite connection used as a
context manager commits its transaction and stays open, which is a leak that
Python 3.12 says nothing about and 3.13 turns into a failure somewhere else.

## The rules are written down

`scowbox.laws` gathers the standing rules in one place, each with the module
that enforces it, and `scowbox book laws` prints them. Nothing reads it to make
a decision; it exists so that a reader who has arrived at a quantity they did
not expect has the list in front of them.

## Orchestration is a layer

`scowbox.job.quantities` reads records out, hands them to the rules and hands
the answer back. It holds no rules of its own. `scowbox.report` turns answers
into lists of lines and `scowbox.cli` is the only thing that prints them.
