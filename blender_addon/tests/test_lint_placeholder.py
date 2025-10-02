"""Placeholder explaining lint is enforced via pre-commit.

We intentionally do not run Ruff from inside pytest (keeps output clean).
Coverage threshold enforced via --cov-fail-under in pyproject.toml.
"""


def test_placeholder():
    assert True
