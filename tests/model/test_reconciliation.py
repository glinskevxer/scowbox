"""What a reconciliation record has to carry."""

from __future__ import annotations

import datetime as dt

import pytest

from scowbox.errors import FieldError
from scowbox.model.reconciliation import Accepted, Reconciliation
from scowbox.units.volume import Yards

DAY = dt.date(2025, 11, 4)


def a_record(**over: object) -> Reconciliation:
    fields: dict[str, object] = {
        "reach": "RCH-012",
        "decided_on": DAY,
        "accepted": Accepted.SURVEY,
        "decided_by": "R. Beaufort, resident engineer",
        "note": "",
        "quantity": None,
    }
    fields.update(over)
    return Reconciliation(**fields)  # type: ignore[arg-type]


def test_only_an_agreed_figure_needs_a_quantity() -> None:
    assert Accepted.AGREED.needs_quantity
    assert not Accepted.SURVEY.needs_quantity
    assert not Accepted.SCOW.needs_quantity


def test_accepting_a_measurement_carries_no_figure() -> None:
    assert a_record().quantity is None
    assert a_record(accepted=Accepted.SCOW).quantity is None


def test_accepting_a_measurement_and_a_figure_is_refused() -> None:
    with pytest.raises(FieldError, match="takes that figure"):
        a_record(quantity=Yards.of_yards(1000))


def test_an_agreed_figure_needs_a_quantity() -> None:
    with pytest.raises(FieldError) as caught:
        a_record(accepted=Accepted.AGREED, note="split the difference")
    assert caught.value.field == "quantity"


def test_an_agreed_figure_needs_a_note() -> None:
    with pytest.raises(FieldError) as caught:
        a_record(accepted=Accepted.AGREED, quantity=Yards.of_yards(1000))
    assert caught.value.field == "note"


def test_an_agreed_figure_is_not_negative() -> None:
    with pytest.raises(FieldError):
        a_record(accepted=Accepted.AGREED, quantity=Yards.of_yards(-1), note="split the difference")
    assert (
        a_record(accepted=Accepted.AGREED, quantity=Yards.zero(), note="nothing paid").quantity
        == Yards.zero()
    )


def test_a_reconciliation_names_who_decided_it() -> None:
    with pytest.raises(FieldError):
        a_record(decided_by="  ")


def test_a_reconciliation_needs_a_reach_identifier() -> None:
    with pytest.raises(FieldError):
        a_record(reach="SV-0031")


def test_describe_reads_as_a_file_note() -> None:
    assert a_record().describe() == (
        "RCH-012 settled 2025-11-04 by R. Beaufort, resident engineer: survey"
    )


def test_an_agreed_figure_prints_in_the_description() -> None:
    text = a_record(
        accepted=Accepted.AGREED, quantity=Yards.of_yards(24000), note="split"
    ).describe()
    assert text.endswith("agreed figure, 24,000 cy")
