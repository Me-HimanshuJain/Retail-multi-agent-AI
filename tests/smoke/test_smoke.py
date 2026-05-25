from __future__ import annotations


def test_core_imports():
    import src.core  # noqa: F401
    import src.api  # noqa: F401
    import src.simulation  # noqa: F401
    import src.models  # noqa: F401


def test_readme_exists():
    import os

    assert os.path.exists("README.md")
