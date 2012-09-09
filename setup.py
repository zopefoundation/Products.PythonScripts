##############################################################################
#
# Copyright (c) 2010 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################

from setuptools import setup, find_packages

setup(name='Products.PythonScripts',
      version = '2.13.3dev',
      url='http://pypi.python.org/pypi/Products.PythonScripts',
      license='ZPL 2.1',
      description="Provides support for restricted execution of Python "
                  "scripts in Zope 2.",
      author='Zope Foundation and Contributors',
      author_email='zope-dev@zope.org',
      long_description=open('README.txt').read() + '\n' +
                       open('CHANGES.txt').read(),
      packages=find_packages('src'),
      namespace_packages=['Products'],
      package_dir={'': 'src'},
      install_requires=[
        'setuptools',
        'AccessControl',
        'Acquisition',
        'DateTime',
        'DocumentTemplate',
        'RestrictedPython',
        'zExceptions',
        'Zope2 >= 2.13.0a1',
      ],
      include_package_data=True,
      zip_safe=False,
      )
