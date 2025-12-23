"""Stationing reads and writes the way a survey drawing does."""

from __future__ import annotations

import pytest

from scowbox.errors import FieldError
from scowbox.units.station import Reachline, Station


def test_parse_reads_a_whole_station() -> None:
    assert Station.parse("12+50").hundredths == 125000
    assert Station.parse("0+00").hundredths == 0


def test_parse_carries_the_hundredths() -> None:
    assert Station.parse("12+50.25").hundredths == 125025
    assert Station.parse("3+07.5").hundredths == 30750


def test_parse_accepts_a_station_behind_the_start() -> None:
    assert Station.parse("-1+50").hundredths == -15000


@pytest.mark.parametrize("text", ["1250", "12-50", "12+5", "12+050", "", "12+50.257"])
def test_parse_refuses_anything_that_is_not_stationing(text: str) -> None:
    with pytest.raises(FieldError):
        Station.parse(text)


def test_stationing_text_round_trips_exactly() -> None:
    for text in ["0+00", "12+50", "12+50.25", "137+04.10", "-1+50"]:
        assert str(Station.parse(text)) == text


def test_of_feet_rounds_to_the_hundredth() -> None:
    assert Station.of_feet(1250.254).hundredths == 125025
    assert str(Station.of_feet(1250)) == "12+50"


def test_stations_order_by_distance() -> None:
    assert Station.parse("9+99") < Station.parse("10+00")
    assert max(Station.parse("2+00"), Station.parse("11+00")) == Station.parse("11+00")


def test_adding_feet_moves_ahead() -> None:
    assert Station.parse("12+50") + 100 == Station.parse("13+50")
    assert Station.parse("12+50") + (-50) == Station.parse("12+00")


def test_subtracting_two_stations_gives_feet() -> None:
    assert Station.parse("13+50") - Station.parse("12+50") == 100.0
    assert Station.parse("12+50.25") - Station.parse("12+50") == 0.25


def test_a_run_knows_its_length() -> None:
    run = Reachline.parse("100+00", "104+00")
    assert run.length == 400.0
    assert str(run) == "100+00 to 104+00"


def test_a_run_must_run_ahead() -> None:
    with pytest.raises(FieldError):
        Reachline.parse("104+00", "100+00")
    with pytest.raises(FieldError):
        Reachline.parse("100+00", "100+00")


def test_holds_excludes_the_ahead_station() -> None:
    run = Reachline.parse("100+00", "104+00")
    assert run.holds(Station.parse("100+00"))
    assert run.holds(Station.parse("103+99"))
    assert not run.holds(Station.parse("104+00"))
    assert not run.holds(Station.parse("99+99"))


def test_adjoining_runs_do_not_overlap() -> None:
    first = Reachline.parse("100+00", "104+00")
    second = Reachline.parse("104+00", "108+00")
    assert not first.overlaps(second)
    assert not second.overlaps(first)


def test_runs_that_share_length_overlap_both_ways() -> None:
    first = Reachline.parse("100+00", "104+00")
    inside = Reachline.parse("101+00", "102+00")
    assert first.overlaps(inside)
    assert inside.overlaps(first)


def test_cuts_land_on_the_interval_and_end_on_the_run() -> None:
    run = Reachline.parse("100+00", "104+00")
    assert [str(s) for s in run.cuts(100)] == [
        "100+00",
        "101+00",
        "102+00",
        "103+00",
        "104+00",
    ]


def test_a_short_last_interval_is_kept_as_it_is() -> None:
    run = Reachline.parse("100+00", "102+50")
    assert [str(s) for s in run.cuts(100)] == ["100+00", "101+00", "102+00", "102+50"]


def test_cuts_refuses_an_interval_of_nothing() -> None:
    with pytest.raises(FieldError):
        Reachline.parse("100+00", "104+00").cuts(0)
