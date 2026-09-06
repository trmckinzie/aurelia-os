"""Shared minimal-but-valid profile.json fixture for tests/test_profile.py and
tests/test_pipeline.py -- kept in one place so the two suites can't drift
into testing against subtly different shapes of "a valid profile"."""


def minimal_profile():
    """Returns a fresh dict passing engine.profile.validate_profile() as-is.

    A fresh dict each call -- callers are free to mutate the result (e.g. to
    corrupt one field for a negative test) without affecting other tests.
    """
    return {
        "schema_version": 1,
        "identity": {
            "name": "Ada Lovelace",
            "headline": "Analyst & Metaphysician",
            "location": "London, England",
            "summary": "Wrote the first published algorithm intended for implementation on a computer.",
        },
        "roles": [
            {
                "org": "Analytical Engine Project",
                "title": "Analyst",
                "period": "1842 — 1843",
                "description": "Translated and annotated Menabrea's memoir on the Analytical Engine.",
                "primary": True,
            }
        ],
        "education": [
            {
                "institution": "Self-taught (private tutors)",
                "credential": "Mathematics & Science",
                "period": "1820s — 1830s",
            }
        ],
        "skills": [
            {"group": "Mathematics", "items": ["Algebra", "Analytical Engines"]}
        ],
        "projects": [
            {
                "name": "Notes on the Analytical Engine",
                "description": "An annotated translation describing an algorithm for the Bernoulli numbers.",
                "tags": ["Algorithms"],
                "status": "archived",
            }
        ],
        "links": [
            {"label": "Email", "url": "mailto:ada@example.com", "kind": "email"},
        ],
        "meta": {
            "updated": "2026-09-05",
        },
    }
