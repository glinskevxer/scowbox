"""Surveys and shots, including what happens when shots are loaded twice."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.errors import DuplicateError, MissingError
from scowbox.model.channel import Method, Reach, Template
from scowbox.model.survey import Sounding, Survey, SurveyKind
from scowbox.store import reaches, surveys
from scowbox.store.book import book
from scowbox.units.clock import moment
from scowbox.units.depth import Depth
from scowbox.units.station import Reachline, Station

DAY = dt.date(2025, 3, 14)


@pytest.fixture
def open_book(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with book(tmp_path / "book.sqlite3", create=True) as connection:
        reaches.add(
            connection,
            Reach(
                ident="RCH-012",
                name="Lower Range",
                line=Reachline.parse("100+00", "140+00"),
                template=Template(
                    bottom_width=400,
                    authorized_depth=Depth.of_feet(42),
                    side_slope=3,
                    advance_maintenance=2,
                    overdepth=2,
                ),
                method=Method.SURVEY,
                group="base",
            ),
        )
        yield connection


def a_shot(offset: float = 0.0, depth: float = 40.0, station: str = "100+00") -> Sounding:
    return Sounding(
        station=Station.parse(station),
        offset=offset,
        raw_depth=Depth.of_feet(depth),
        taken=moment(DAY, "07:45"),
    )


def a_survey(ident: str = "SV-0031", **over: object) -> Survey:
    fields: dict[str, object] = {
        "ident": ident,
        "reach": "RCH-012",
        "kind": SurveyKind.BEFORE,
        "taken_on": DAY,
        "vessel": "Cape Fear",
        "transducer_draft": 2.5,
        "soundings": (),
    }
    fields.update(over)
    return Survey(**fields)  # type: ignore[arg-type]


def test_a_header_round_trips(open_book: sqlite3.Connection) -> None:
    surveys.add(open_book, a_survey())
    assert surveys.get(open_book, "SV-0031") == a_survey()


def test_shots_written_with_the_header_come_back(open_book: sqlite3.Connection) -> None:
    surveys.add(open_book, a_survey(soundings=(a_shot(-50), a_shot(50))))
    back = surveys.full(open_book, "SV-0031")
    assert [s.offset for s in back.soundings] == [-50, 50]


def test_shots_come_back_in_station_and_offset_order(open_book: sqlite3.Connection) -> None:
    surveys.add(open_book, a_survey())
    surveys.load(
        open_book,
        "SV-0031",
        [a_shot(50, station="101+00"), a_shot(50), a_shot(-50)],
    )
    back = surveys.full(open_book, "SV-0031")
    assert [(str(s.station), s.offset) for s in back.soundings] == [
        ("100+00", -50.0),
        ("100+00", 50.0),
        ("101+00", 50.0),
    ]


def test_a_shot_keeps_its_zone_through_the_book(open_book: sqlite3.Connection) -> None:
    surveys.add(open_book, a_survey(soundings=(a_shot(),)))
    back = surveys.full(open_book, "SV-0031")
    assert back.soundings[0].taken == moment(DAY, "07:45")


def test_loading_replaces_rather_than_appends(open_book: sqlite3.Connection) -> None:
    surveys.add(open_book, a_survey(soundings=(a_shot(-50), a_shot(50))))
    gone, arrived = surveys.load(open_book, "SV-0031", [a_shot(0)])
    assert (gone, arrived) == (2, 1)
    assert surveys.full(open_book, "SV-0031").count == 1


def test_loading_onto_a_survey_that_is_not_there_says_so(open_book: sqlite3.Connection) -> None:
    with pytest.raises(MissingError):
        surveys.load(open_book, "SV-0099", [a_shot()])


def test_a_survey_of_a_reach_that_is_not_there_is_refused(
    open_book: sqlite3.Connection,
) -> None:
    with pytest.raises(MissingError) as caught:
        surveys.add(open_book, a_survey(reach="RCH-999"))
    assert caught.value.kind == "reach"


def test_the_same_survey_twice_is_a_duplicate(open_book: sqlite3.Connection) -> None:
    surveys.add(open_book, a_survey())
    with pytest.raises(DuplicateError):
        surveys.add(open_book, a_survey())


def test_surveys_of_a_reach_come_back_oldest_first(open_book: sqlite3.Connection) -> None:
    surveys.add(open_book, a_survey("SV-0032", taken_on=dt.date(2025, 4, 1)))
    surveys.add(open_book, a_survey("SV-0031"))
    assert [s.ident for s in surveys.for_reach(open_book, "RCH-012")] == ["SV-0031", "SV-0032"]
    assert surveys.for_reach(open_book, "RCH-999") == ()


def test_every_survey_in_the_book_is_listed(open_book: sqlite3.Connection) -> None:
    surveys.add(open_book, a_survey("SV-0031"))
    surveys.add(open_book, a_survey("SV-0032", kind=SurveyKind.AFTER))
    assert len(surveys.listed(open_book)) == 2


def test_removing_a_survey_takes_its_shots_with_it(open_book: sqlite3.Connection) -> None:
    surveys.add(open_book, a_survey(soundings=(a_shot(),)))
    surveys.remove(open_book, "SV-0031")
    with pytest.raises(MissingError):
        surveys.get(open_book, "SV-0031")


def test_removing_a_survey_that_is_not_there_says_so(open_book: sqlite3.Connection) -> None:
    with pytest.raises(MissingError):
        surveys.remove(open_book, "SV-0099")
