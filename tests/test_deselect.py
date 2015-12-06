import subprocess
import os.path

import pytest


def from_here(*args):
    return os.path.join(os.path.dirname(__file__), *args)


@pytest.mark.external_dependencies
@pytest.mark.parametrize('sequence', [
    (('simple01.py', b'1 passed'),
     ('simple01.py', b'1 deselected')),

    (('simple01.py', b'1 passed'),
     ('simple01_fail.py', b'1 failed')),

    (('external_deps01.py', b'1 passed'),
     ('external_deps01.py', b'1 passed')),
])
def test_deselect(sequence, tmpdir):
    for filename, expected in sequence:
        with open(from_here('files', filename), 'r') as s:
            f = tmpdir.join('test.py')
            f.write(s.read())

        p = subprocess.run(['py.test', 'test.py'],
                           cwd=str(tmpdir),
                           stdout=subprocess.PIPE)

        assert expected in p.stdout
