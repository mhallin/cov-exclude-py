import pytest


@pytest.fixture
def sample_fixture():
    return True


def test_fixture(sample_fixture):
    assert sample_fixture
