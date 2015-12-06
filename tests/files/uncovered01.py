def helper(a, b):
    if a == b:
        return True
    else:
        return False


def test_helper_true():
    assert helper(5, 5)
