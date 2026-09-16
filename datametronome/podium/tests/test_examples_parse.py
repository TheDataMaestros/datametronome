"""Every shipped example YAML must import.

Three of the six examples did not parse. Two described a config format and
check types the loader has never implemented, and one used a `stave:` key the
loader does not read. Nothing caught it: the YAML tests build their own
fixtures, and the one test that touched a real example skipped when the file
was missing and swallowed parse errors in a try/except.

An example that cannot be imported is worse than no example. This fails
instead.
"""

from pathlib import Path

import pytest

from datametronome_podium.services.yaml_loader import load_and_parse_yaml

EXAMPLES = sorted((Path(__file__).parent.parent / "examples").glob("*.yaml"))

# Deliberately invalid: the loader's conflict-detection tests import it.
KNOWN_INVALID = {"conflicting-config.yaml"}


def test_there_are_examples_to_check():
    # A glob that silently matches nothing would make every test below pass.
    assert EXAMPLES, "no example YAML files found"


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_example_parses(path):
    if path.name in KNOWN_INVALID:
        pytest.skip(reason="intentionally invalid fixture")

    staves, clefs = load_and_parse_yaml(str(path))

    assert staves, f"{path.name} declares no staves"
    for clef in clefs:
        assert clef.stave_id, f"{path.name}: clef {clef.name!r} has no stave_id"
        known = {s.id for s in staves}
        assert clef.stave_id in known, (
            f"{path.name}: clef {clef.name!r} points at stave "
            f"{clef.stave_id!r}, which the file does not define"
        )
