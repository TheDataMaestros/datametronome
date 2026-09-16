"""No class may define the same method twice.

ClefExecutor defined _execute_forecast_check and
_execute_data_profile_drift_check twice each. The earlier pair were mocks that
returned status "pass" with a made-up score. Python keeps the last definition,
so the real implementations won and the mocks sat there unreachable.

That is one file reorder away from a data quality tool reporting every drift
and forecast check as green. Nothing catches it: the file imports, the tests
pass, and both definitions read as correct on their own.
"""

import ast
from pathlib import Path

import pytest

SOURCE = Path(__file__).parent.parent / "datametronome_podium"
FILES = sorted(SOURCE.rglob("*.py"))


def _duplicate_methods(path: Path) -> list[str]:
    tree = ast.parse(path.read_text())
    found = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        seen: dict[str, int] = {}
        for item in node.body:
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            # A property and its setter share a name legitimately.
            decorators = {
                d.attr if isinstance(d, ast.Attribute) else getattr(d, "id", "")
                for d in item.decorator_list
            }
            if decorators & {"setter", "getter", "deleter", "overload", "register"}:
                continue
            if item.name in seen:
                found.append(
                    f"{node.name}.{item.name} defined at line {seen[item.name]} "
                    f"and again at line {item.lineno}"
                )
            seen[item.name] = item.lineno

    return found


def test_there_are_files_to_check():
    assert FILES, "no source files found"


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_no_duplicate_method_definitions(path):
    duplicates = _duplicate_methods(path)
    assert not duplicates, f"{path.name}: " + "; ".join(duplicates)
