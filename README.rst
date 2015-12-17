======================================
 Pytest Coverage-based Test Exclusion
======================================

.. image:: https://api.travis-ci.org/mhallin/cov-exclude-py.svg?branch=master
   :target: https://travis-ci.org/mhallin/cov-exclude-py

.. image:: https://img.shields.io/pypi/v/pytest-cov-exclude.svg
   :target: https://pypi.python.org/pypi/pytest-cov-exclude

Coverage-based test exclusion plugin for pytest_. By looking at which
lines are executed by each test, the next test run can be sped up by
*not* executing the tests where no source files have changed.

If you have a large test suite which you often re-run, this plugin can
drastically improve the iteration times.


Installation
============

Install with pip:

.. code-block:: text

   $ pip install pytest-cov-exclude

``pytest-cov-exclude`` requires Pytest 2.8 or later. It is compatible with
Python 2.7, 3.3, 3.4, 3.5, as well as PyPy. It does *not* work on PyPy
3 due to an unknown bug with the coverage data generated.


Usage
=====

The first time you run your test suite, per-test coverage is enabled
and the suite will take a *little bit* longer than usual:

.. code-block:: text

   $ py.test

   ==================== test session starts =====================

   # Test output...

   ================ MANY passed in MANY seconds =================

Now when you re-run the test suite, all tests should have been
excluded:

.. code-block:: text

   $ py.test

   ==================== test session starts =====================

   # Test output...

   =============== MANY deselected in FEW seconds ===============

If a test fails, it will re-run even if nothing changed in order to
preserve the general failure status of the test suite.


Forcing individual test inclusion
---------------------------------

If you have tests that depend on files not included in coverage data,
such as data files or generated sources, you can mark the tests with
``external_dependencies``. This forces them to be re-run even if no
files were changed:

.. code-block:: python

   @pytest.mark.external_dependencies
   def test_something():
       # Run tests from external data files


Known bugs
----------

* Changes to files during pytest's collection phase will be
  ignored. Test files and their dependencies are scanned as soon as
  possible *after* the test collection is complete.

  There is a test case marked ``xfail`` that highlights this issue.


Running the whole test suite
----------------------------

If you want to force a complete re-run of the whole test suite, you
have two options: either disable the plugin, or clear pytest's cache:

.. code-block:: text

   $ py.test -p no:cov-exclude  # Disable the plugin

   $ py.test --cache-clear  # Clear pytest's cache


Compatibility
=============

As stated earlier, this plugin requires Pytest 2.8 or later since it
depends on the new cache module.

While PyPy is supported, the ujson_ library used for faster
serialization/deserialization is not available, so a fallback to the
default JSON implementation is used instead. Because of this, the
tests might actually run *slower* with this plugin under PyPy.

.. _pytest: http://pytest.org
.. _ujson: https://pypi.python.org/pypi/ujson
