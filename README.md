# scowbox

Measurement and payment for a maintenance dredging contract.

Hydrographic surveys and scow box measure sheets go in. Pay quantities and
monthly progress estimates come out.

## What it is for

A federal maintenance dredging contract is measured two ways at once. A pair of
surveys says how much the bed moved. A stack of box measure sheets says how much
came out of the water in the scows. The two never agree, because they are not
measuring the same thing, and the contract has a third body of rules for
deciding which of them you may bill.

This is the office side of that: the book that holds the records, the
arithmetic that turns them into quantities, and the rules that decide which
quantity is the one on the estimate.

## Install

    python -m pip install -e ".[dev]" -c constraints.txt

## Use

    scowbox --book harbour.sqlite3 init
    scowbox --book harbour.sqlite3 reach add RCH-012 "Lower Range" \
        --begin 100+00 --end 140+00 --bottom 600 --depth 42 \
        --advance 2 --overdepth 2 --method both
    scowbox --book harbour.sqlite3 tide load 8658120 gauge.csv
    scowbox --book harbour.sqlite3 survey add SV-0031 RCH-012 --kind before \
        --on 2025-03-03 --vessel "Cape Fear" --draft 2.0 --gauge 8658120
    scowbox --book harbour.sqlite3 survey load SV-0031 before.csv
    scowbox --book harbour.sqlite3 quantity reach RCH-012
    scowbox --book harbour.sqlite3 estimate write --through 2025-04-30

`docs/commands.md` is the full command reference, `docs/schema.md` the schema
and `docs/glossary.md` every closed vocabulary in the package. All three are
generated, and CI fails if any of them has gone stale.

## Shape

    units model                 measures and records
    datum section boxmeasure    reducing, sectioning and box measuring
    windows measure pay         rules, and rules about rules
    compliance store feed       the sweep, the book and the file readers
    job report cli              the work, the pages and the terminal
    tools                       the checks the build runs on itself

Nothing imports upward, nothing outside `store` opens a database, nothing
outside `cli` prints, and nothing anywhere asks the machine what day it is.
Each of those is a check rather than a convention.

## Check

    python -m ruff check .
    python -m ruff format --check .
    python -m mypy
    python -m pytest -q
    python -m scowbox.tools.smoke
