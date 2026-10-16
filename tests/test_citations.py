"""APA 7 references and Pandoc citations for essays (roadmap S16).

Golden strings for every rule docs/ESSAYS.md ("Citations") names: each of
the five source types, one, two, three to twenty and twenty-one or more
authors, a group author, 1979a and 1979b, DOI over URL, en-dash page
ranges, list order and italics; then each citation form, the email address
that is not one, and the warnings that fail the strict build. The build-level
proof that a strict build stops on a missing or an uncited record is in
tests/test_essays.py, beside the other build tests.
"""
import pytest

from engine.buildlog import get_warnings, reset_warnings
from engine.citations import (
    References,
    edition_label,
    en_dash,
    format_entry,
    initials,
    locator_text,
    parse_bracket,
)
from engine.content import make_id
from engine.essays import check_reference_records, render_body


@pytest.fixture(autouse=True)
def _clean_warnings():
    reset_warnings()
    yield
    reset_warnings()


def person(family, given):
    return {"family": family, "given": given}


KT = [person("Kahneman", "Daniel"), person("Tversky", "Amos")]

JOURNAL = {
    "id": "kahneman1979", "type": "article-journal", "author": KT, "issued": 1979,
    "title": "Prospect theory: An analysis of decision under risk", "container-title": "Econometrica",
    "volume": 47, "issue": 2, "page": "263-291", "DOI": "10.2307/1914185", "verified": True,
}
BOOK = {
    "id": "kahneman2011", "type": "book", "author": [person("Kahneman", "Daniel")], "issued": 2011,
    "title": "Thinking, fast and slow", "edition": 2, "publisher": "Farrar, Straus and Giroux",
    "verified": True,
}
CHAPTER = {
    "id": "kahneman1982", "type": "chapter", "author": KT,
    "editor": [person("Kahneman", "Daniel"), person("Slovic", "Paul"), person("Tversky", "Amos")],
    "issued": 1982, "title": "The simulation heuristic",
    "container-title": "Judgment under uncertainty: Heuristics and biases", "page": "201-208",
    "publisher": "Cambridge University Press", "verified": False,
}
ENCYCLOPEDIA = {
    "id": "steele2020", "type": "entry-encyclopedia",
    "author": [person("Steele", "Katie"), person("Stefánsson", "H. Orri")],
    "editor": [person("Zalta", "Edward N.")], "issued": 2020, "title": "Decision theory",
    "container-title": "The Stanford encyclopedia of philosophy", "version": "Winter 2020 Edition",
    "publisher": "Metaphysics Research Lab, Stanford University",
    "URL": "https://plato.stanford.edu/archives/win2020/entries/decision-theory/", "verified": True,
}
PREPRINT = {
    "id": "lee2023", "type": "article", "genre": "Preprint",
    "author": [person("Lee", "Ana"), person("Kim", "Bo"), person("Park", "Cy")], "issued": 2023,
    "title": "Does loss aversion replicate online?", "publisher": "PsyArXiv",
    "DOI": "https://doi.org/10.31234/osf.io/abcde", "URL": "https://osf.io/abcde", "verified": True,
}
GROUP = {
    "id": "apa2020", "type": "book", "author": [{"literal": "American Psychological Association"}],
    "issued": 2020, "title": "Publication manual of the American Psychological Association", "edition": 7,
    "publisher": "American Psychological Association", "DOI": "10.1037/0000165-000", "verified": True,
}


def entry(record, year=None):
    return str(format_entry(record, year or str(record["issued"])))


# --- the five types -------------------------------------------------------

def test_journal_article():
    assert entry(JOURNAL) == (
        "Kahneman, D., &amp; Tversky, A. (1979). Prospect theory: An analysis of decision under risk. "
        "<i>Econometrica</i>, <i>47</i>(2), 263–291. "
        '<a href="https://doi.org/10.2307/1914185">https://doi.org/10.2307/1914185</a>'
    )


def test_journal_article_without_issue_or_link():
    record = {**JOURNAL, "issue": None, "DOI": None}
    assert entry(record) == (
        "Kahneman, D., &amp; Tversky, A. (1979). Prospect theory: An analysis of decision under risk. "
        "<i>Econometrica</i>, <i>47</i>, 263–291."
    )


def test_authored_book_with_edition():
    assert entry(BOOK) == (
        "Kahneman, D. (2011). <i>Thinking, fast and slow</i> (2nd ed.). Farrar, Straus and Giroux."
    )


def test_a_first_edition_is_not_mentioned():
    assert entry({**BOOK, "edition": 1}) == (
        "Kahneman, D. (2011). <i>Thinking, fast and slow</i>. Farrar, Straus and Giroux."
    )


def test_chapter_in_an_edited_book():
    assert entry(CHAPTER) == (
        "Kahneman, D., &amp; Tversky, A. (1982). The simulation heuristic. "
        "In D. Kahneman, P. Slovic, &amp; A. Tversky (Eds.), "
        "<i>Judgment under uncertainty: Heuristics and biases</i> (pp. 201–208). Cambridge University Press."
    )


def test_chapter_with_one_editor_two_editors_and_an_edition():
    one = {**CHAPTER, "editor": [person("Slovic", "Paul")], "edition": "3"}
    assert "In P. Slovic (Ed.), <i>Judgment under uncertainty: Heuristics and biases</i> (3rd ed., pp. 201–208)." in entry(one)
    two = {**CHAPTER, "editor": [person("Slovic", "Paul"), person("Tversky", "Amos")]}
    assert "In P. Slovic &amp; A. Tversky (Eds.), " in entry(two)


def test_encyclopedia_entry_in_the_stanford_shape():
    assert entry(ENCYCLOPEDIA) == (
        "Steele, K., &amp; Stefánsson, H. O. (2020). Decision theory. In E. N. Zalta (Ed.), "
        "<i>The Stanford encyclopedia of philosophy</i> (Winter 2020 ed.). "
        "Metaphysics Research Lab, Stanford University. "
        '<a href="https://plato.stanford.edu/archives/win2020/entries/decision-theory/">'
        "https://plato.stanford.edu/archives/win2020/entries/decision-theory/</a>"
    )


def test_preprint():
    assert entry(PREPRINT) == (
        "Lee, A., Kim, B., &amp; Park, C. (2023). <i>Does loss aversion replicate online?</i> [Preprint]. "
        'PsyArXiv. <a href="https://doi.org/10.31234/osf.io/abcde">https://doi.org/10.31234/osf.io/abcde</a>'
    )


def test_a_preprint_without_a_genre_is_still_labelled_one():
    assert "[Preprint]" in entry({**PREPRINT, "genre": None})


# --- authors --------------------------------------------------------------

def test_one_two_and_three_authors():
    assert entry({**BOOK}).startswith("Kahneman, D. (2011).")
    assert entry({**BOOK, "author": KT}).startswith("Kahneman, D., &amp; Tversky, A. (2011).")
    three = KT + [person("Thaler", "Richard H.")]
    assert entry({**BOOK, "author": three}).startswith("Kahneman, D., Tversky, A., &amp; Thaler, R. H. (2011).")


def test_twenty_authors_are_all_listed():
    names = [person(f"Author{i}", "X.") for i in range(1, 21)]
    head = entry({**BOOK, "author": names}).split(" (2011)")[0]
    assert head == ", ".join(f"Author{i}, X." for i in range(1, 20)) + ", &amp; Author20, X."


def test_twenty_one_or_more_authors_list_nineteen_an_ellipsis_and_the_last():
    names = [person(f"Author{i}", "X.") for i in range(1, 26)]
    head = entry({**BOOK, "author": names}).split(" (2011)")[0]
    assert head == ", ".join(f"Author{i}, X." for i in range(1, 20)) + ", . . . Author25, X."
    assert "Author20" not in head and "&amp;" not in head


def test_a_group_author_and_a_publisher_it_already_names():
    assert entry(GROUP) == (
        "American Psychological Association. (2020). "
        "<i>Publication manual of the American Psychological Association</i> (7th ed.). "
        '<a href="https://doi.org/10.1037/0000165-000">https://doi.org/10.1037/0000165-000</a>'
    )


def test_initials():
    assert initials("Daniel") == "D."
    assert initials("Jane A.") == "J. A."
    assert initials("Jean-Paul") == "J.-P."
    assert initials("J.R.R.") == "J. R. R."
    assert initials(None) == ""
    assert entry({**BOOK, "author": [{"family": "Plato"}]}).startswith("Plato. (2011).")


# --- the other rules ------------------------------------------------------

def test_doi_is_preferred_over_url_and_normalised_to_doi_org():
    assert "https://osf.io/abcde" not in entry(PREPRINT)
    for written in ("10.2307/1914185", "doi:10.2307/1914185", "https://dx.doi.org/10.2307/1914185"):
        assert '<a href="https://doi.org/10.2307/1914185">https://doi.org/10.2307/1914185</a>' in entry({**JOURNAL, "DOI": written})


def test_page_ranges_take_an_en_dash():
    assert en_dash("263-291") == "263–291"
    assert en_dash("263 — 291") == "263–291"
    assert en_dash("e1001") == "e1001"
    assert locator_text("p. 12-15") == "pp. 12–15"
    assert locator_text("p. 12") == "p. 12"
    assert locator_text("chap. 3") == "chap. 3"


def test_edition_labels():
    assert edition_label(2) == "2nd ed."
    assert edition_label("3") == "3rd ed."
    assert edition_label(11) == "11th ed."
    assert edition_label(22) == "22nd ed."
    assert edition_label("Fall 2021 Edition") == "Fall 2021 ed."
    assert edition_label("Rev.") == "Rev. ed."
    assert edition_label(1) is None


def test_titles_keep_their_case_and_their_own_closing_mark():
    record = {**JOURNAL, "title": "Does iPhone use predict DNA damage?"}
    assert "(1979). Does iPhone use predict DNA damage? <i>Econometrica</i>" in entry(record)
    assert "<i>Why we sleep?</i> (2nd ed.)." in entry({**BOOK, "title": "Why we sleep?"})


def test_every_field_is_escaped():
    record = {**BOOK, "title": "<script>alert(1)</script>", "publisher": "A & B"}
    html = entry(record)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html and "A &amp; B." in html


def _refs(*records):
    return References(list(records), "E09", "E09.refs.yaml")


def test_same_authors_same_year_are_lettered_by_title():
    later = {**JOURNAL, "id": "kahneman1979a", "title": "Intuitive prediction: Biases and corrective procedures",
             "container-title": "TIMS Studies in Management Science", "volume": 12, "issue": None,
             "page": "313-327", "DOI": None}
    refs = _refs(JOURNAL, later)
    assert [e["key"] for e in refs.entries()] == ["kahneman1979a", "kahneman1979"]
    assert "(1979a). Intuitive prediction" in str(refs.entries()[0]["html"])
    assert "(1979b). Prospect theory" in str(refs.entries()[1]["html"])
    # A leading article does not count when lettering or ordering.
    the = {**later, "id": "the", "title": "The zebra problem"}
    refs = _refs(JOURNAL, the)
    assert [e["key"] for e in refs.entries()] == ["kahneman1979", "the"]


def test_list_order_is_first_author_then_year_then_title():
    thaler = {**JOURNAL, "id": "thaler1980", "author": [person("Thaler", "Richard H.")], "issued": 1980}
    knetsch = {**JOURNAL, "id": "kahneman1990", "issued": 1990,
               "author": [person("Kahneman", "Daniel"), person("Knetsch", "Jack L."), person("Thaler", "Richard H.")]}
    refs = _refs(thaler, CHAPTER, JOURNAL, knetsch, BOOK, GROUP, ENCYCLOPEDIA, PREPRINT)
    assert [e["key"] for e in refs.entries()] == [
        "apa2020",        # American ...
        "kahneman2011",   # Kahneman alone comes before Kahneman with others
        "kahneman1990",   # Kahneman, Knetsch ... before Kahneman, Tversky
        "kahneman1979",   # Kahneman & Tversky by year
        "kahneman1982",
        "lee2023",
        "steele2020",
        "thaler1980",
    ]


def test_order_is_letter_by_letter_and_ignores_accents():
    a = {**BOOK, "id": "a", "author": [person("de Vries", "A.")]}
    b = {**BOOK, "id": "b", "author": [person("Devine", "B.")]}
    c = {**BOOK, "id": "c", "author": [person("Écuyer", "C.")]}
    assert [e["key"] for e in _refs(c, b, a).entries()] == ["b", "a", "c"]   # devine < devries < ecuyer


def test_italics_fall_where_apa_7_puts_them():
    assert "<i>Econometrica</i>, <i>47</i>(2)" in entry(JOURNAL)           # journal title and volume, not issue
    assert entry(JOURNAL).count("<i>") == 2                               # the article title stays roman
    assert "<i>Thinking, fast and slow</i>" in entry(BOOK)
    assert "The simulation heuristic. In" in entry(CHAPTER)               # chapter roman, book italic
    assert "<i>Judgment under uncertainty: Heuristics and biases</i>" in entry(CHAPTER)
    assert "<i>The Stanford encyclopedia of philosophy</i>" in entry(ENCYCLOPEDIA)
    assert "<i>Does loss aversion replicate online?</i>" in entry(PREPRINT)


# --- the reference file's shape (fails every build) -----------------------

def test_verified_is_required_on_every_record():
    assert check_reference_records([JOURNAL]) == []
    without = {k: v for k, v in JOURNAL.items() if k != "verified"}
    assert any("verified: required" in p for p in check_reference_records([without]))
    assert any("verified: required" in p for p in check_reference_records([{**JOURNAL, "verified": "yes"}]))


@pytest.mark.parametrize("names, message", [
    ([{"family": "Kahneman", "given": "Daniel", "note": "summary"}], "unknown field 'note'"),
    ([{"given": "Daniel"}], "needs family"),
    ([{"literal": "APA", "family": "x"}], "literal alone"),
    ([], "non-empty list of names"),
    ("Kahneman, D.", "non-empty list of names"),
])
def test_names_are_checked_against_their_own_allowlist(names, message):
    problems = check_reference_records([{**JOURNAL, "author": names}])
    assert any(message in p for p in problems), problems


@pytest.mark.parametrize("issued", ["1979", 79, True, 1979.0])
def test_a_wrongly_typed_year_fails_every_build(issued):
    assert any("issued: must be a four-digit year" in p
               for p in check_reference_records([{**JOURNAL, "issued": issued}]))


@pytest.mark.parametrize("key", ["kahneman 1979", "kahneman1979.", "<b>", "-x"])
def test_a_key_must_be_a_citation_key(key):
    assert any("is not a citation key" in p for p in check_reference_records([{**JOURNAL, "id": key}]))


# --- what only warns (fails the strict build) -----------------------------

def test_an_unsupported_type_or_an_incomplete_record_warns_and_is_left_out():
    thesis = {**BOOK, "id": "thesis", "type": "thesis"}
    no_year = {**BOOK, "id": "noyear", "issued": None}
    no_journal = {**JOURNAL, "id": "nojournal", "container-title": None}
    refs = _refs(BOOK, thesis, no_year, no_journal)
    assert [e["key"] for e in refs.entries()] == ["kahneman2011"]
    warnings = get_warnings()
    assert any("'thesis'" in w and "not one the APA 7 formatter supports" in w for w in warnings)
    assert any("'noyear'" in w and "four-digit year" in w for w in warnings)
    assert any("'nojournal'" in w and "needs container-title" in w for w in warnings)


def test_a_duplicate_key_warns_and_keeps_the_first():
    refs = _refs(BOOK, {**BOOK, "title": "Another"})
    assert len(refs.entries()) == 1
    assert "fast and slow" in str(refs.entries()[0]["html"])
    assert any("appears more than once" in w for w in get_warnings())


def test_two_works_that_would_cite_alike_warn():
    a = {**PREPRINT, "id": "a"}
    b = {**PREPRINT, "id": "b", "author": [person("Lee", "Ana"), person("Moss", "Di"), person("Ng", "Ed")]}
    _refs(a, b)
    assert any("would both cite as (Lee et al., 2023)" in w for w in get_warnings())


# --- citations in the text ------------------------------------------------

FIXTURE_REFS = [JOURNAL, BOOK, CHAPTER, GROUP,
                {**JOURNAL, "id": "thaler1980", "author": [person("Thaler", "Richard H.")], "issued": 1980},
                {**PREPRINT, "id": "lee2023"}]


def cite(text, records=FIXTURE_REFS):
    refs = _refs(*records)
    html = str(render_body(text, "E09", make_id, set(), "/garden.html", refs))
    return html.removeprefix("<p>").removesuffix("</p>\n"), refs


def link(key, text):
    return f'<a href="#ref-{key}" class="essay-citation">{text}</a>'


def test_parenthetical():
    html, _ = cite("[@kahneman1979]")
    assert html == "(" + link("kahneman1979", "Kahneman &amp; Tversky, 1979") + ")"


def test_page_locator():
    html, _ = cite("[@kahneman1979, p. 263]")
    assert html == "(" + link("kahneman1979", "Kahneman &amp; Tversky, 1979, p. 263") + ")"
    html, _ = cite("[@kahneman1979 pp. 263-265]")
    assert html == "(" + link("kahneman1979", "Kahneman &amp; Tversky, 1979, pp. 263–265") + ")"


def test_several_sources_in_reference_list_order():
    html, _ = cite("[@thaler1980; @kahneman1979]")
    assert html == ("(" + link("kahneman1979", "Kahneman &amp; Tversky, 1979") + "; "
                    + link("thaler1980", "Thaler, 1980") + ")")


def test_same_authors_share_one_name_in_a_citation():
    html, _ = cite("[@kahneman1982; @kahneman1979]")
    assert html == ("(" + link("kahneman1979", "Kahneman &amp; Tversky, 1979") + ", "
                    + link("kahneman1982", "1982") + ")")


def test_narrative():
    html, _ = cite("@kahneman1979 argue that losses loom larger.")
    assert html == link("kahneman1979", "Kahneman and Tversky (1979)") + " argue that losses loom larger."
    html, _ = cite("As @kahneman2011 [p. 300] puts it.")
    assert html == "As " + link("kahneman2011", "Kahneman (2011, p. 300)") + " puts it."
    html, _ = cite("@lee2023 disagree.")
    assert html == link("lee2023", "Lee et al. (2023)") + " disagree."


def test_group_author_prefix_and_suppressed_author():
    html, _ = cite("[see @apa2020, sec. 8.12]")
    assert html == "(see " + link("apa2020", "American Psychological Association, 2020, sec. 8.12") + ")"
    html, _ = cite("Kahneman and Tversky [-@kahneman1979] argue.")
    assert html == "Kahneman and Tversky (" + link("kahneman1979", "1979") + ") argue."


def test_an_email_address_a_url_path_and_an_escaped_at_sign_are_not_citations():
    html, refs = cite("Write to kahneman1979@example.com, see https://example.com/@kahneman1979, "
                      "or \\@kahneman1979 and \\@someone.")
    assert html == ("Write to kahneman1979@example.com, see https://example.com/@kahneman1979, "
                    "or @kahneman1979 and @someone.")
    assert refs.cited == set()
    assert get_warnings() == []


def test_a_misspelled_narrative_citation_renders_as_written_and_warns():
    # The reference is cited correctly elsewhere, so the uncited-record net
    # alone would not catch the typo.
    html, refs = cite("As @kahnman1979 argued [@kahneman1979].", [JOURNAL])
    assert html.startswith("As @kahnman1979 argued (")
    refs.warn_uncited()
    assert get_warnings() == ["Essay E09: @kahnman1979 reads as a citation but has no record in "
                              "E09.refs.yaml; write \\@kahnman1979 if it is not one"]


def test_an_image_whose_alt_text_starts_with_an_at_sign_stays_an_image():
    html, refs = cite("![@kahneman1979](figure.png)")
    assert html.startswith('<img src="figure.png" alt="@kahneman1979"')
    assert refs.cited == set()


def test_a_field_the_type_does_not_show_warns_but_the_entry_still_renders():
    refs = _refs({**JOURNAL, "edition": 2}, {**PREPRINT, "page": "1-10"})
    assert len(refs.entries()) == 2
    warnings = get_warnings()
    assert any("'kahneman1979'" in w and "has edition" in w for w in warnings)
    assert any("'lee2023'" in w and "has page" in w for w in warnings)
    assert _refs(JOURNAL, BOOK, CHAPTER, ENCYCLOPEDIA, PREPRINT, GROUP) and not [
        w for w in get_warnings()[2:] if "does not show" in w]


def test_a_preprint_by_its_own_server_names_it_once():
    record = {**PREPRINT, "author": [{"literal": "PsyArXiv"}]}
    assert entry(record).count("PsyArXiv") == 1


def test_citation_syntax_in_code_or_a_link_stays_literal():
    html, refs = cite("`[@kahneman1979]` and [@kahneman1979](https://example.com)")
    assert "<code>[@kahneman1979]</code>" in html
    assert '<a href="https://example.com" rel="noopener noreferrer">@kahneman1979</a>' in html
    assert refs.cited == set()


def test_a_citation_with_no_record_warns_and_renders_as_written():
    html, _ = cite("[@kahneman1979; @nobody2020]")
    assert html == '<span class="essay-missing-citation">[@kahneman1979; @nobody2020]</span>'
    assert any("cites 'nobody2020', which has no record in E09.refs.yaml" in w for w in get_warnings())


def test_a_record_nothing_cites_warns():
    _html, refs = cite("[@kahneman1979]", [JOURNAL, BOOK])
    refs.warn_uncited()
    assert get_warnings() == ["Essay E09: reference 'kahneman2011' in E09.refs.yaml is cited nowhere in the essay"]


def test_without_a_reference_file_citation_syntax_is_left_alone():
    html = str(render_body("[@kahneman1979] and @kahneman1979", "E09", make_id, set(), "/garden.html"))
    assert html == "<p>[@kahneman1979] and @kahneman1979</p>\n"


def test_parse_bracket():
    assert parse_bracket("@a") == [("", "a", "", False)]
    assert parse_bracket("see @a, p. 3; -@b") == [("see", "a", "p. 3", False), ("", "b", "", True)]
    assert parse_bracket("just text") is None
    assert parse_bracket("x@a") is None
    assert parse_bracket("@a.") is None
