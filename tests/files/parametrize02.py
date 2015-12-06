import pytest


@pytest.mark.parametrize('x,y', [
    (1, 2),
    (2, 5),
    (3, 6),
])
def test_doubling(x, y):
    assert 2 * x == y
