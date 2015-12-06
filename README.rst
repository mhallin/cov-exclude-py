===========================
 Pytest Coverage Exclusion
===========================

.. image:: https://api.travis-ci.org/mhallin/cov-exclude-py.svg?branch=master
   :target: https://travis-ci.org/mhallin/cov-exclude-py

Coverage-based test exclusion plugin for pytest_. By looking at which
lines are executed by each test, the next test run can be sped up by
*not* executing the tests where no source files have changed.

If you have a large test suite which you often re-run, this plugin can
drastically improve the iteration times.


Installation
============

Install with pip:

.. code-block:: text

   $ pip install cov-exclude

``cov-exclude`` requires Pytest 2.8 or later.

Usage
=====

The first time you run your test suite, per-test coverage is enabled
and the suite will take a *little bit* longer than usual:

.. code-block:: text

   $ py.test

   ==================== test session starts =====================

   # Test output...

   ================ MANY passed in LOTS seconds =================

Now when you re-run the test suite, all tests should have been
excluded:

.. code-block:: text

   $ py.test

   ==================== test session starts =====================

   # Test output...

   =============== MANY deselected in FEW seconds ===============


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


Running the whole test suite
----------------------------

If you want to force a complete re-run of the whole test suite, you
have two options: either disable the plugin, or clear pytest's cache:

.. code-block:: text

   $ py.test -p no:cov-exclude  # Disable the plugin

   $ py.test --cache-clear  # Clear pytest's cache


.. _pytest: http://pytest.org
