import time


def test_slow():
    time.sleep(0)
    assert False
