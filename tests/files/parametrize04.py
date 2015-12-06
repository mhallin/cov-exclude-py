import pytest


@pytest.mark.parametrize('xs,y', [
    ([1, 1], 2),
    ([2, 3], 4),
    ([3, 3], 6),
])
def test_sum(xs, y):
    assert sum(xs) == y
