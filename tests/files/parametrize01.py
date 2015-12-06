import pytest


@pytest.mark.parametrize('x,y', [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_doubling(x, y):
    assert 2 * x == y
