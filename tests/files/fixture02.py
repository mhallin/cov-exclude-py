import pytest


@pytest.fixture
def sample_fixture():
    return False


def test_fixture(sample_fixture):
    assert sample_fixture
