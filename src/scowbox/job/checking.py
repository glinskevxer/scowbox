"""Reading a survey in the book back for quality.

The template a survey is measured against is the template of the reach it was
run over, which is in the book next to it. Passing one in would let a survey be
checked against a cut it was never run to, and the only thing that would look
wrong about the answer is that it was right.
"""

from __future__ import annotations

import sqlite3

from scowbox.datum.reduce import reduce_survey
from scowbox.job.quantities import tide_for
from scowbox.measure.quality import NEARBY_FEET, Quality, quality
from scowbox.store import reaches, surveys


def check_survey(
    connection: sqlite3.Connection,
    ident: str,
    *,
    nearby: float = NEARBY_FEET,
    share: float = 0.9,
    squat: float = 0.0,
    index: float = 0.0,
) -> Quality:
    """Reduce a survey in the book and read it back for quality."""
    survey = surveys.full(connection, ident)
    reach = reaches.get(connection, survey.reach)
    shots = reduce_survey(survey, tide_for(connection, survey), squat=squat, index=index)
    return quality(shots, reach.template, nearby=nearby, share=share)
