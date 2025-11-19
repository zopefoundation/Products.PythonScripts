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

from setuptools import setup


setup(name='Products.PythonScripts',
      version='5.2.dev0',
      url='https://github.com/zopefoundation/Products.PythonScripts',
      project_urls={
          'Issue Tracker': ('https://github.com/zopefoundation/'
                            'Products.PythonScripts/issues'),
          'Sources': ('https://github.com/zopefoundation/'
                      'Products.PythonScripts'),
      },
      license='ZPL-2.1',
      description='Provides support for restricted execution of Python '
                  'scripts in Zope.',
      author='Zope Foundation and Contributors',
      author_email='zope-dev@zope.dev',
      long_description=('{}\n{}'.format(open('README.rst').read(),
                                        open('CHANGES.rst').read())),
      classifiers=[
          'Development Status :: 6 - Mature',
          'Environment :: Web Environment',
          'Framework :: Zope',
          'Framework :: Zope :: 5',
          'License :: OSI Approved :: Zope Public License',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.10',
          'Programming Language :: Python :: 3.11',
          'Programming Language :: Python :: 3.12',
          'Programming Language :: Python :: 3.13',
          'Programming Language :: Python :: 3.14',
          'Programming Language :: Python :: Implementation :: CPython',
      ],
      python_requires='>=3.10',
      install_requires=[
          'AccessControl',
          'Acquisition',
          'DateTime',
          'DocumentTemplate',
          'RestrictedPython >= 4.0b5',
          'zExceptions',
          'Zope >= 4.1.2',
      ],
      entry_points={
          'zodbupdate.decode': [
              'decodes = Products.PythonScripts:zodbupdate_decode_dict',
          ],
      },
      include_package_data=True,
      )
