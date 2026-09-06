import os

import pytest

import build
from engine import pipeline
from engine.content import dim_dangling_links
from engine.pipeline import (
    _build_graph_index,
    _build_link_graph,
    _build_lobby_context,
    _degree_from_edges,
)
from tests.profile_fixtures import minimal_profile
from tests.test_paths import make_dir_link


def _card(note_id, title, body, tags=None):
    return {"id": note_id, "title": title, "body": body, "type": "CONCEPT", "tags": tags or []}


def _lobby_card(note_id, title, maturity=""):
    return {"id": note_id, "title": title, "maturity": maturity}


def test_link_graph_backlinks_maps_target_to_referencing_notes():
    cards = [
        _card("note-a", "A", "links to <button onclick=\"openNote('note-b')\">B</button>"),
        _card("note-b", "B", "no links here"),
        _card("note-c", "C", "also links to <button onclick=\"openNote('note-b')\">B</button>"),
    ]
    backlinks, _ = _build_link_graph(cards)
    assert backlinks == {"note-b": [{"id": "note-a", "title": "A"}, {"id": "note-c", "title": "C"}]}


def test_link_graph_omits_notes_with_no_incoming_links():
    cards = [_card("note-a", "A", "no links"), _card("note-b", "B", "also no links")]
    backlinks, edges = _build_link_graph(cards)
    assert backlinks == {}
    assert edges == []


def test_link_graph_ignores_self_links():
    cards = [_card("note-a", "A", "links to itself: <button onclick=\"openNote('note-a')\">A</button>")]
    backlinks, edges = _build_link_graph(cards)
    assert backlinks == {}
    assert edges == []


def test_link_graph_ignores_links_to_unpublished_notes():
    # note-ghost isn't in the card list at all (e.g. unpublished or a
    # scrapped page type), so it can't appear as a backlink target or edge.
    cards = [_card("note-a", "A", "links to <button onclick=\"openNote('note-ghost')\">Ghost</button>")]
    backlinks, edges = _build_link_graph(cards)
    assert backlinks == {}
    assert edges == []


def test_link_graph_dedupes_multiple_links_from_the_same_note():
    cards = [
        _card("note-a", "A", "mentions B twice: "
              "<button onclick=\"openNote('note-b')\">B</button> and again "
              "<button onclick=\"openNote('note-b')\">B</button>"),
        _card("note-b", "B", "no links"),
    ]
    backlinks, edges = _build_link_graph(cards)
    assert backlinks == {"note-b": [{"id": "note-a", "title": "A"}]}
    assert edges == [{"source": "note-a", "target": "note-b"}]


def test_link_graph_edges_are_deduped_undirected_pairs():
    # A links to B and B links back to A -- one edge, not two.
    cards = [
        _card("note-a", "A", "<button onclick=\"openNote('note-b')\">B</button>"),
        _card("note-b", "B", "<button onclick=\"openNote('note-a')\">A</button>"),
    ]
    _, edges = _build_link_graph(cards)
    assert edges == [{"source": "note-a", "target": "note-b"}]


def test_graph_index_nodes_carry_id_title_type_tags():
    cards = [_card("note-a", "A", "", tags=["topic/x"])]
    index = _build_graph_index(cards, edges=[])
    assert index["nodes"] == [{"id": "note-a", "title": "A", "type": "concept", "tags": ["topic/x"]}]
    assert index["edges"] == []


def test_lobby_context_counts_notes_and_maturity():
    cards = [
        _lobby_card("note-a", "A", "seed"),
        _lobby_card("note-b", "B", "seed"),
        _lobby_card("note-c", "C", "evergreen"),
        _lobby_card("note-d", "D", ""),  # no maturity tag at all
    ]
    graph_index = {"nodes": [], "edges": []}
    stats = _build_lobby_context(cards, graph_index)
    assert stats["total_notes"] == 4
    assert stats["maturity_counts"] == {"seed": 2, "growing": 0, "evergreen": 1}


def test_lobby_context_ranks_hub_notes_by_connection_count():
    cards = [_lobby_card("note-a", "A"), _lobby_card("note-b", "B"), _lobby_card("note-c", "C")]
    graph_index = {
        "nodes": [
            {"id": "note-a", "title": "A", "type": "concept"},
            {"id": "note-b", "title": "B", "type": "source"},
            {"id": "note-c", "title": "C", "type": "concept"},
        ],
        "edges": [{"source": "note-a", "target": "note-b"}, {"source": "note-a", "target": "note-c"}],
    }
    stats = _build_lobby_context(cards, graph_index)
    assert stats["hub_notes"][0] == {"id": "note-a", "title": "A", "type": "concept", "connections": 2}


def test_lobby_context_finds_latest_daily_log_date():
    cards = [
        _lobby_card("note-2025-01-01", "2025-01-01"),
        _lobby_card("note-2025-12-31", "2025-12-31"),
        _lobby_card("note-some-concept", "Some Concept"),  # not a daily log
    ]
    graph_index = {"nodes": [], "edges": []}
    stats = _build_lobby_context(cards, graph_index)
    assert stats["latest_log_date"] == "2025-12-31"


def test_lobby_context_latest_log_date_is_none_without_daily_logs():
    cards = [_lobby_card("note-some-concept", "Some Concept")]
    graph_index = {"nodes": [], "edges": []}
    stats = _build_lobby_context(cards, graph_index)
    assert stats["latest_log_date"] is None


def test_lobby_context_review_seed_carries_id_title_maturity():
    cards = [_lobby_card("note-a", "A", "seed")]
    graph_index = {"nodes": [], "edges": []}
    stats = _build_lobby_context(cards, graph_index)
    assert stats["review_seed"] == [{"id": "note-a", "title": "A", "maturity": "seed"}]


def test_degree_from_edges_counts_both_endpoints():
    edges = [
        {"source": "note-a", "target": "note-b"},
        {"source": "note-b", "target": "note-c"},
    ]
    degree = _degree_from_edges(edges)
    assert degree["note-a"] == 1
    assert degree["note-b"] == 2   # appears as both a source and a target
    assert degree["note-c"] == 1


def test_degree_from_edges_is_empty_for_no_edges():
    assert _degree_from_edges([]) == {}


def test_link_graph_is_identical_whether_or_not_dangling_links_were_dimmed():
    """Regression guard for the ordering change that let cards show a
    connection count.

    _build_link_graph used to run on the finished cards, whose bodies had
    been through dim_dangling_links() -- which rewrites openNote() buttons
    whose target isn't published into plain spans. It now runs earlier, on
    the un-dimmed body, so strictly more candidate targets reach it. That
    must not change the graph: the function already discards any target not
    in the known set. If someone later removes that guard, this fails.
    """
    body = (
        "real <button onclick=\"openNote('note-b')\">B</button> and "
        "dangling <button onclick=\"openNote('note-ghost')\">Ghost</button>"
    )
    known = {"note-a", "note-b"}

    undimmed = [_card("note-a", "A", body), _card("note-b", "B", "")]
    dimmed = [_card("note-a", "A", dim_dangling_links(body, known)), _card("note-b", "B", "")]

    assert _build_link_graph(undimmed) == _build_link_graph(dimmed)


# --- _scan_vault publish gating (audit #25) --------------------------------
#
# Every test below builds its own vault under pytest's tmp_path and points
# engine.pipeline.VAULT_PATH at it. The real vault/ is never read or written.

def _write_note(vault, relpath, frontmatter, body="Body text.\n"):
    path = vault / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter}\n---\n{body}", encoding="utf-8")
    return path


def _scan(vault, monkeypatch):
    monkeypatch.setattr(pipeline, "VAULT_PATH", str(vault))
    garden_cards, _, _ = pipeline._scan_vault()
    return {c["title"] for c in garden_cards}


def test_scan_vault_publishes_only_notes_flagged_true(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    _write_note(vault, "10_GARDEN/Published.md", "publish: true\ntype: concept")
    _write_note(vault, "10_GARDEN/Unpublished.md", "publish: false\ntype: concept")
    # Audit #23: bool("false") was True, so this one published itself.
    _write_note(vault, "10_GARDEN/Quoted False.md", 'publish: "false"\ntype: concept')
    # Audit #23: an unrecognized value must not publish either.
    _write_note(vault, "10_GARDEN/Ambiguous.md", "publish: maybe\ntype: concept")

    assert _scan(vault, monkeypatch) == {"Published"}


def test_scan_vault_skips_20_aurelia_even_when_publish_is_true(tmp_path, monkeypatch):
    # Agent-drafted notes (aurelia-mcp-server's draft_note, ARCHITECTURE.md
    # Rule 4). An agent emitting `publish: true` must not thereby publish
    # itself to a public site.
    vault = tmp_path / "vault"
    _write_note(vault, "10_GARDEN/Real Note.md", "publish: true\ntype: concept")
    _write_note(vault, "20_AURELIA/Agent Draft.md", "publish: true\ntype: concept")
    _write_note(vault, "20_AURELIA/nested/Deeper Draft.md", "publish: true\ntype: concept")

    assert _scan(vault, monkeypatch) == {"Real Note"}


@pytest.mark.parametrize("folder", ["20_Aurelia", "20_aurelia", "20_AureliA"])
def test_scan_vault_prunes_the_agent_draft_folder_whatever_its_casing(folder, tmp_path, monkeypatch):
    """NTFS is case-insensitive and its casing is sticky.

    If 20_AURELIA is ever first created as 20_Aurelia -- by a tool, a
    restore, a hand-typed mkdir -- an exact-match prune fails open from then
    on, permanently and with no error, and agent-drafted notes carrying
    `publish: true` become publishable.
    """
    vault = tmp_path / "vault"
    _write_note(vault, "10_GARDEN/Real Note.md", "publish: true\ntype: concept")
    _write_note(vault, f"{folder}/Agent Draft.md", "publish: true\ntype: concept")

    assert _scan(vault, monkeypatch) == {"Real Note"}


def test_scan_vault_does_not_publish_through_a_directory_junction(tmp_path, monkeypatch):
    """A junction planted under vault/ must not publish external notes.

    On Windows os.path.islink() is False for a junction, so os.walk descends
    it with followlinks=False and every .md under it looks like an ordinary
    vault note -- `publish: true` and all. Creating one needs no elevation.
    The containment check on the resolved path is what stops it; see
    engine/paths.py. Verified against the unfixed code: the walk reached
    External Secret.md and published it.
    """
    vault = tmp_path / "vault"
    _write_note(vault, "10_GARDEN/Real Note.md", "publish: true\ntype: concept")

    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "External Secret.md").write_text(
        "---\npublish: true\ntype: concept\n---\nNot vault content.\n", encoding="utf-8")
    make_dir_link(vault / "10_GARDEN" / "linked", outside)

    assert _scan(vault, monkeypatch) == {"Real Note"}


def test_scan_vault_still_reads_a_junction_that_stays_inside_the_vault(tmp_path, monkeypatch):
    # Containment, not a blanket ban on links: a vault synced or organized
    # through a junction that lands back inside itself still publishes.
    vault = tmp_path / "vault"
    _write_note(vault, "10_GARDEN/Real Note.md", "publish: true\ntype: concept")
    _write_note(vault, "10_GARDEN/nested/Inner.md", "publish: true\ntype: concept")
    make_dir_link(vault / "alias", vault / "10_GARDEN" / "nested")

    assert _scan(vault, monkeypatch) == {"Real Note", "Inner"}


def test_scan_vault_reads_frontmatter_past_a_triple_dash_value(tmp_path, monkeypatch):
    # Audit #24: the fence used to be found mid-value, so `publish:` below it
    # was never parsed and the note silently vanished from the site.
    vault = tmp_path / "vault"
    _write_note(
        vault, "10_GARDEN/Dashed.md",
        "title: Before---After\npublish: true\ntype: concept",
    )
    assert _scan(vault, monkeypatch) == {"Dashed"}


def test_scan_vault_keeps_a_body_horizontal_rule_out_of_the_frontmatter(tmp_path, monkeypatch):
    # Audit #24, other direction: a horizontal rule in the body must not be
    # mistaken for the opening fence of anything.
    vault = tmp_path / "vault"
    _write_note(
        vault, "10_GARDEN/Ruled.md",
        "publish: true\ntype: concept",
        body="Intro paragraph.\n\n---\n\nAfter the rule.\n",
    )
    monkeypatch.setattr(pipeline, "VAULT_PATH", str(vault))
    garden_cards, _, _ = pipeline._scan_vault()
    assert [c["title"] for c in garden_cards] == ["Ruled"]
    assert "After the rule." in garden_cards[0]["body"]


# --- the build can be told not to touch vault/ (audit #26) -----------------
#
# organize_assets() moves files inside vault/. These tests must never call the
# real one, and must never let the real build run -- so every collaborator is
# stubbed and _scan_vault raises immediately after the decision under test.

class _StopBuild(Exception):
    """Ends build_all() right after the drop-zone decision."""


def _stub_build_steps(monkeypatch):
    calls = []
    monkeypatch.setattr(pipeline, "prepare_dist", lambda: calls.append("prepare_dist"))
    monkeypatch.setattr(pipeline, "organize_assets", lambda: calls.append("organize_assets"))
    monkeypatch.setattr(pipeline, "sync_vault_assets", lambda: calls.append("sync_vault_assets"))

    def _stop():
        raise _StopBuild

    monkeypatch.setattr(pipeline, "_scan_vault", _stop)
    return calls


def test_build_all_sorts_the_dropzone_by_default(monkeypatch):
    monkeypatch.delenv("AURELIA_SKIP_DROPZONE", raising=False)
    calls = _stub_build_steps(monkeypatch)
    with pytest.raises(_StopBuild):
        pipeline.build_all()
    assert "organize_assets" in calls


def test_build_all_no_sort_does_not_call_organize_assets(monkeypatch):
    monkeypatch.delenv("AURELIA_SKIP_DROPZONE", raising=False)
    calls = _stub_build_steps(monkeypatch)
    with pytest.raises(_StopBuild):
        pipeline.build_all(sort_dropzone=False)
    assert "organize_assets" not in calls
    # The rest of the build still happens -- this skips a vault mutation, not
    # a build step that produces dist/.
    assert calls == ["prepare_dist", "sync_vault_assets"]


def test_build_all_env_var_skips_the_dropzone_sort(monkeypatch):
    monkeypatch.setenv("AURELIA_SKIP_DROPZONE", "1")
    calls = _stub_build_steps(monkeypatch)
    with pytest.raises(_StopBuild):
        pipeline.build_all()
    assert "organize_assets" not in calls


def test_explicit_sort_dropzone_true_overrides_the_env_var(monkeypatch):
    monkeypatch.setenv("AURELIA_SKIP_DROPZONE", "1")
    calls = _stub_build_steps(monkeypatch)
    with pytest.raises(_StopBuild):
        pipeline.build_all(sort_dropzone=True)
    assert "organize_assets" in calls


@pytest.mark.parametrize("value", ["", "0", "false", "no", "off", "FALSE"])
def test_env_var_falsey_values_still_sort(monkeypatch, value):
    monkeypatch.setenv("AURELIA_SKIP_DROPZONE", value)
    assert pipeline.skip_dropzone_env() is False


@pytest.mark.parametrize("value", ["1", "true", "yes", "anything"])
def test_env_var_truthy_values_skip(monkeypatch, value):
    monkeypatch.setenv("AURELIA_SKIP_DROPZONE", value)
    assert pipeline.skip_dropzone_env() is True


# --- a broken render must fail the build ----------------------------------

def _render_args():
    """Minimal arguments for _render_pages(); the render itself is stubbed."""
    return dict(
        user_config={}, garden_cards=[], json_index="{}", backlinks_json="{}",
        graph_json="{}", lobby_stats={}, review_seed_json="{}", deep_search_json="{}",
        profile=minimal_profile(),
    )


def test_render_failure_raises_instead_of_exiting_zero(tmp_path, monkeypatch):
    """A template error used to print and continue.

    `python build.py` then exited 0 with a page missing, and CI -- which
    runs only the build -- deployed that dist/ under a green check. A
    previous session's template typo was swallowed exactly here.
    """
    monkeypatch.setattr(pipeline, "OUTPUT_DIR", str(tmp_path))

    class BrokenEnv:
        def get_template(self, name):
            raise ValueError("unexpected '%' in template")

    monkeypatch.setattr(pipeline, "env", BrokenEnv())

    with pytest.raises(RuntimeError, match="index.html"):
        pipeline._render_pages(**_render_args())


def test_render_failure_stops_before_writing_the_remaining_pages(tmp_path, monkeypatch):
    # A half-rendered dist/ is the outcome being prevented, so the first
    # failure aborts rather than pressing on to the next page.
    monkeypatch.setattr(pipeline, "OUTPUT_DIR", str(tmp_path))

    class BrokenEnv:
        def get_template(self, name):
            raise ValueError("boom")

    monkeypatch.setattr(pipeline, "env", BrokenEnv())

    with pytest.raises(RuntimeError):
        pipeline._render_pages(**_render_args())

    assert not (tmp_path / "garden.html").exists()
    assert not (tmp_path / "404.html").exists()


def test_ci_workflow_builds_with_the_vault_guard_on():
    """CI must pass --no-sort.

    Without it the deploy job runs organize_assets() in the runner, moving
    vault/99_DROP_ZONE/ into vault/assets/<kind>/ -- which sync_vault_assets()
    then copies into the published dist/ with no `publish:` gate. The guard
    exists (this module's build_all docstring names CI as the reason); it
    just was not being used, and nothing but this test notices.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    workflow = os.path.join(root, ".github", "workflows", "deploy.yml")
    with open(workflow, encoding="utf-8") as f:
        body = f.read()

    build_lines = [ln.strip() for ln in body.splitlines() if "build.py" in ln and "#" not in ln]
    assert build_lines, "no build.py invocation found in the deploy workflow"
    for line in build_lines:
        assert "--no-sort" in line, f"CI build must pass --no-sort: {line}"


def test_build_cli_maps_no_sort_to_sort_dropzone_false():
    # Absent flag stays None so the env var still gets a say; --no-sort is a
    # hard False.
    assert build.parse_args([]).no_sort is False
    assert build.parse_args(["--no-sort"]).no_sort is True
