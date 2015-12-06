import subprocess
import os.path

import pytest


def from_here(*args):
    return os.path.join(os.path.dirname(__file__), *args)


def run_test_file(filename, tmpdir):
    with open(from_here('files', filename), 'r') as s:
        f = tmpdir.join('test.py')
        f.write(s.read())

    if tmpdir.join('__pycache__').check():
        tmpdir.join('__pycache__').remove()

    if tmpdir.join('test.pyc').check():
        tmpdir.join('test.pyc').remove()

    p = subprocess.Popen(['py.test', '-v', 'test.py'],
                         cwd=str(tmpdir),
                         stdout=subprocess.PIPE)
    stdout, _ = p.communicate()

    return stdout


@pytest.mark.external_dependencies
@pytest.mark.parametrize('sequence', [
    # Do *not* deselect failing tests
    (('simple01.py', b'1 passed'),
     ('simple01_fail.py', b'1 failed'),
     ('simple01_fail.py', b'1 failed'),
     ('simple01.py', b'1 passed')),

    # Do *not* deselect tests with external dependencies
    (('external_deps01.py', b'1 passed'),
     ('external_deps01.py', b'1 passed')),

    # Deselect tests where the source changes are not covered by the
    # test function
    (('uncovered01.py', b'1 passed'),
     ('uncovered02.py', b'1 deselected')),

    # Changes made to whitespace between covered blocks should still
    # be counted, even if the line technically wasn't executed
    (('whitespace01.py', b'1 passed'),
     ('whitespace02.py', b'1 failed')),

    # Changes made to the last line can be tricky to pick up
    (('whitespace03.py', b'1 passed'),
     ('whitespace04.py', b'1 failed')),

    # Changes made to fixtures should be picked up
    (('fixture01.py', b'1 passed'),
     ('fixture02.py', b'1 failed')),

    # Changes made to parametrized definitions should be picked up,
    # but we don't really care about how many of the parameters were
    # selected/deselected.
    (('parametrize01.py', b'3 passed'),
     ('parametrize02.py', b'1 failed')),

    # In order to not depend on the *name* of a parameterized test,
    # run the parametrized tests with more intricate data structures
    (('parametrize03.py', b'3 passed'),
     ('parametrize04.py', b'1 failed')),
])
def test_run_changes(sequence, tmpdir):
    """Running each sequence of files should provide the expected output
    each sequence has defined.

    """
    assert not tmpdir.join('.cache').check()

    for filename, expected in sequence:
        stdout = run_test_file(filename, tmpdir)

        assert expected in stdout


@pytest.mark.external_dependencies
@pytest.mark.parametrize('filename,n_tests', [
    ('simple01.py', 1),
    ('uncovered01.py', 1),
    ('whitespace01.py', 1),
    ('whitespace03.py', 1),
    ('fixture01.py', 1),
    ('parametrize01.py', 3),
])
def test_deselect_nochange(filename, n_tests, tmpdir):
    """Running the same file twice in succession should deselect all tests"""

    assert not tmpdir.join('.cache').check()

    expect_pass = '{} passed'.format(n_tests).encode('ascii')
    expect_deselect = '{} deselected'.format(n_tests).encode('ascii')

    stdout_pass = run_test_file(filename, tmpdir)
    assert expect_pass in stdout_pass

    stdout_deselect = run_test_file(filename, tmpdir)
    assert expect_deselect in stdout_deselect
