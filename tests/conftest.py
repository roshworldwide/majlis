import pytest

from majlis.kb.store import load_chunks


@pytest.fixture(scope="session")
def chunks():
    return load_chunks()


@pytest.fixture(scope="session")
def by_id(chunks):
    return {c["chunk_id"]: c for c in chunks}
