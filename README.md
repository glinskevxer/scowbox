# scowbox

Maintenance dredging measurement and payment.

Hydrographic surveys and scow box measure sheets go in. Pay quantities and
monthly progress estimates come out.

## Install

    python -m pip install -e ".[dev]" -c constraints.txt

## Check

    python -m ruff check .
    python -m ruff format --check .
    python -m mypy
    python -m pytest -q
