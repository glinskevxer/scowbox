"""Check: nothing imports upward.

The package is a stack. Units know nothing about records, records know nothing
about rules, rules know nothing about the database, the database knows nothing
about reports and only the command line knows about all of it.

That order is the reason a rule can be tested without a book and a report can
be tested without a terminal. It survives exactly as long as somebody is
checking it: the first import of ``store`` from inside ``measure`` will be
completely reasonable in the moment and will take the whole arrangement with it.
"""

from __future__ import annotations

import sys

from scowbox.tools.scan import Module, modules, report

NAME = "check_layers"

LAYERS: tuple[tuple[str, ...], ...] = (
    ("errors", "ids"),
    ("units",),
    ("model",),
    ("datum", "section", "boxmeasure", "windows"),
    ("measure", "pay"),
    ("compliance",),
    ("store",),
    ("feed",),
    ("job",),
    ("report",),
    ("cli",),
    ("tools",),
)

_DEPTH = {name: depth for depth, names in enumerate(LAYERS) for name in names}


def layer_of(name: str) -> int | None:
    """Which layer a dotted module name sits in, or nothing for the package root."""
    parts = name.split(".")
    if len(parts) < 2:
        return None
    return _DEPTH.get(parts[1])


def findings(found: list[Module] | None = None) -> list[str]:
    """Every import that points up the stack."""
    out = []
    for module in found if found is not None else modules():
        mine = layer_of(module.name)
        if mine is None:
            continue
        for imported in sorted(set(module.imports())):
            theirs = layer_of(imported)
            if theirs is None or theirs <= mine:
                continue
            out.append(f"{module.where} (layer {mine}) imports {imported} (layer {theirs})")
    return out


def unplaced(found: list[Module] | None = None) -> list[str]:
    """Modules that sit in no layer at all, which the check cannot see."""
    out = []
    for module in found if found is not None else modules():
        parts = module.name.split(".")
        if len(parts) >= 2 and parts[1] not in _DEPTH:
            out.append(f"{module.where} is in no declared layer")
    return sorted(set(out))


def main() -> int:
    """Run the check and return the exit status."""
    return report(NAME, [*findings(), *unplaced()])


if __name__ == "__main__":
    sys.exit(main())
