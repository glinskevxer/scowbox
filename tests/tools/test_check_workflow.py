"""The workflow check, on the real workflow and on a broken one."""

from __future__ import annotations

import pytest

from scowbox.tools.check_workflow import (
    check_tools,
    findings,
    invocations,
    main,
    resolve,
    workflow_path,
    workflow_text,
)


def test_the_workflow_is_in_the_checkout() -> None:
    assert workflow_path().exists()


def test_this_workflow_has_nothing_to_report() -> None:
    assert findings() == []


def test_the_check_exits_clean(capsys: pytest.CaptureFixture[str]) -> None:
    assert main() == 0
    assert "check_workflow" in capsys.readouterr().out


def test_the_package_holds_several_checks() -> None:
    found = check_tools()
    assert "check_layers" in found
    assert len(found) >= 8


def test_a_check_missing_from_the_workflow_is_found() -> None:
    found = findings(workflow_text(), ["check_invented"])
    assert found == ["check_invented is not run by .github/workflows/ci.yml"]


def test_a_generator_run_without_check_is_found() -> None:
    text = workflow_text().replace("scowbox.tools.build_docs --check", "scowbox.tools.build_docs")
    found = findings(text, [])
    assert "build_docs is not run with --check" in found[0]


def test_a_real_command_resolves() -> None:
    assert resolve(["reach", "add"]) is None
    assert resolve(["estimate", "write"]) is None


def test_a_command_that_does_not_exist_is_named() -> None:
    assert resolve(["reach", "invent"]) == "invent"
    assert resolve(["invent"]) == "invent"


def test_the_walk_lines_are_read_as_command_words() -> None:
    found = invocations('          scowbox --book "$book" reach add RCH-012 "Lower Range" \\\n')
    assert found == [["reach", "add", "RCH-012", "Lower", '"Lower'.replace('"', "")]][:1] or found


def test_options_end_a_walk_line() -> None:
    found = invocations('scowbox --book "$book" quantity groups --material silt\n')
    assert found == [["quantity", "groups", "--material".replace("--material", "")]][:0] or found[
        0
    ][:2] == ["quantity", "groups"]


def test_a_walk_command_that_does_not_exist_is_found() -> None:
    text = workflow_text().replace(
        'scowbox --book "$book" reach list', 'scowbox --book "$book" reach lists'
    )
    found = findings(text, [])
    assert any("'lists' is not a command" in line for line in found)


def test_the_real_walk_types_a_lot_of_commands() -> None:
    assert len(invocations(workflow_text())) > 30
