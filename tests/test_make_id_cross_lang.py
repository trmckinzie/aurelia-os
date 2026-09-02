"""Cross-language contract guard: aurelia-mcp-server's TS makeId()
(packages/vault-reader/src/id.ts) must byte-for-byte agree with this repo's
make_id() (engine/content.py) on every case in tests/fixtures/make_id_cases.json
-- kept byte-identical to aurelia-mcp-server's own copy of that file. See
that file's "_meta" block for the manual sync procedure; there is no
automated sync between these two independent repos/CIs.
"""
import json
import os

import pytest

from engine.content import make_id

_FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "make_id_cases.json")

with open(_FIXTURE_PATH, "r", encoding="utf-8") as f:
    _CASES = json.load(f)["cases"]

# parametrize over an empty list SKIPS rather than fails, so a fixture that
# lost its cases in the manual cross-repo copy would leave the two
# implementations unguarded while pytest still exited 0. Fail loudly instead.
assert _CASES, f"No cases in {_FIXTURE_PATH} -- cross-language guard would silently pass."


@pytest.mark.parametrize("case", _CASES, ids=[c["name"] for c in _CASES])
def test_make_id_matches_typescript_fixture(case):
    assert make_id(case["input"]) == case["expected"]
