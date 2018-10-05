Changelog
=========

4.2 (unreleased)
----------------

- Add support for Python 3.7.

- Drop support for Python 3.4.

- Force recompilation of scripts as the compiled code is now stored
  on `__code__` instead of `func_code`.

- Add a Python 3 compatible default script.
  https://github.com/zopefoundation/Products.PythonScripts/pull/10

- Fix security declaration for ``Products.PythonScripts.standard`` which was
  broken since version 3.0.
  https://github.com/zopefoundation/Zope/issues/209

- Fix HTTP-500 error which occurred when entering code containing a
  syntax error in a PythonScript. It is now rendered as error message like
  other errors.
  (`#11 <https://github.com/zopefoundation/Products.PythonScripts/issues/11>`_)

- Update the tests to `RestrictedPython >= 4.0b4`, thus requiring at lest this
  version.
  (`#17 <https://github.com/zopefoundation/Products.PythonScripts/pull/17>`_)

- Update HTML code of ZMI for Bootstrap ZMI.
  (`#16 <https://github.com/zopefoundation/Products.PythonScripts/pull/16>`_)

- Drop support for historical versions which no longer exist since Zope 4.0a2.


4.1 (2017-06-19)
----------------

- Add support for Python 3.4 up to 3.6.


4.0.1 (2017-02-06)
------------------

- Remove `bobobase_modification_time` from edit template.

4.0 (2016-08-06)
----------------

- Add compatibility with webdav changes in Zope 4.0a2.

.. caution::

    This version needs Zope2 >= 4.0 to run!

3.0 (2016-07-18)
----------------

- Remove HelpSys support.

2.13.2 (2012-09-09)
-------------------

- Correct module security declaration for our `standard` module.

2.13.1 (2012-09-09)
-------------------

- LP #1047318: Adjust tests.

2.13.0 (2010-07-10)
-------------------

- Released as separate package.
