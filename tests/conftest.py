"""Shared fixtures. Every test gets an isolated JSON store in a tmp dir so tools
never touch the real data file and tests don't interfere with each other."""
from __future__ import annotations

import pytest

import clinic.storage as storage


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "STORE_PATH", tmp_path / "store.json")
    yield
