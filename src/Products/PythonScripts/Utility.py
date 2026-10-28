##############################################################################
#
# Copyright (c) 2002 Zope Foundation and Contributors.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE
#
##############################################################################
"""Utility module for making simple security assertions for
   Python scripts."""

from AccessControl import allow_class  # noqa
from AccessControl import allow_module  # noqa
from zope.deprecation import deprecated


deprecated('allow_class',
           'Please import from `AccessControl.SecurityInfo`.'
           'This backwards-compatibility shim will be removed in version 5.5.')


deprecated('allow_module',
           'Please import from `AccessControl.SecurityInfo`.'
           'This backwards-compatibility shim will be removed in version 5.5.')
