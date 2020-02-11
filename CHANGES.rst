Changelog
=========

4.10 (2020-02-11)
-----------------
- override ``manage_DAVget`` to get correct editable sources
  (`#40 <https://github.com/zopefoundation/Products.PythonScripts/issues/40>`_)


4.9 (2019-10-09)
----------------
- prevent ResourceWarning/Error by closing default contents file
  (`#39 <https://github.com/zopefoundation/Products.PythonScripts/issues/39>`_)


4.8 (2019-09-04)
----------------

- Show proper error message for not allowed identifiers.
  (`#33 <https://github.com/zopefoundation/Products.PythonScripts/issues/33>`_)

- Restore History ZMI tab as Zope is supporting it again.
  (`#38 <https://github.com/zopefoundation/Products.PythonScripts/issues/38>`_)


4.7 (2019-05-21)
----------------

- Make sure a template's ``_body`` attribute is a native string in Python 3
  (`#30 <https://github.com/zopefoundation/Products.PythonScripts/issues/30>`_)


4.6 (2019-04-15)
----------------

- Fix a serious error that prevents page templates from compiling
  (`#27 <https://github.com/zopefoundation/Products.PythonScripts/issues/27>`_)


4.5 (2019-04-07)
----------------

- Provide a single default script content template for Python 2 and 3

- Prevent deprecation warning by using ``importlib`` instead of ``imp``
  (`#24 <https://github.com/zopefoundation/Products.PythonScripts/issues/24>`_)

- Prevent syntax warning due to outdated default script content
  (`#26 <https://github.com/zopefoundation/Products.PythonScripts/issues/26>`_)

- Allow for entering a title when adding a Python Script
  (`#25 <https://github.com/zopefoundation/Products.PythonScripts/issues/25>`_)

- adding badges to the README for GitHub and PyPI

- Package metadata cleanups

- cleaned up tox test configuration


4.4 (2019-03-08)
----------------

- Specify supported Python versions using ``python_requires`` in setup.py
  (`Zope#481 <https://github.com/zopefoundation/Zope/issues/481>`_)

- Add support for Python 3.8


4.3 (2019-02-09)
----------------

- Show a message instead of exception for empty file upload
  (`#21 <https://github.com/zopefoundation/Products.PythonScripts/issues/21>`_)


4.2 (2018-10-11)
----------------

- Add support for Python 3.7.

- Drop support for Python 3.4.

- Force recompilation of scripts as the compiled code is now stored
  on `__code__` instead of `func_code`.

- Add a Python 3 compatible default script.
  (`#10 <https://github.com/zopefoundation/Products.PythonScripts/pull/10>`_)

- Fix security declaration for ``Products.PythonScripts.standard`` which was
  broken since version 3.0.
  (`Zope#209 <https://github.com/zopefoundation/Zope/issues/209>`_)

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
