##############################################################################
#
# Copyright (c) 2003 Zope Foundation and Contributors.
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

import unittest

import transaction
from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass
from OFS.Folder import Folder
from OFS.ObjectManager import ObjectManager


class UnderprivilegedUser:

    def getId(self):
        return 'underprivileged'

    def allowed(self, object, object_roles=None):
        return 0


class FauxRoot(ObjectManager):

    def getPhysicalPath(self):
        return ('',)

    def __repr__(self):
        return '<FauxRoot>'


class FauxFolder(Folder):

    security = ClassSecurityInfo()
    security.declareObjectPrivate()

    @security.private
    def __repr__(self):
        return '<FauxFolder: %s>' % self.getId()

    @security.public
    def methodWithRoles(self):
        return 'method called'


InitializeClass(FauxFolder)


class TestBindings(unittest.TestCase):

    def setUp(self):
        from Testing.ZODButil import makeDB
        transaction.begin()
        self.db = makeDB()
        self.connection = self.db.open()

    def tearDown(self):
        from AccessControl.SecurityManagement import noSecurityManager
        from Testing.ZODButil import cleanDB
        noSecurityManager()
        transaction.abort()
        self.connection.close()
        self.db.close()
        cleanDB()

    def _getRoot(self):
        from Testing.makerequest import makerequest
        return makerequest(FauxRoot())

    def _makeTree(self):

        root = self._getRoot()

        guarded = FauxFolder()
        guarded._setId('guarded')
        guarded.__roles__ = ('Manager', )
        root._setOb('guarded', guarded)
        guarded = root._getOb('guarded')

        open = FauxFolder()
        open._setId('open')
        open.__roles__ = ('Anonymous', )
        guarded._setOb('open', open)

        bound_unused_container_ps = self._newPS('return 1')
        guarded._setOb('bound_unused_container_ps', bound_unused_container_ps)

        bound_used_container_ps = self._newPS('return container.id')
        guarded._setOb('bound_used_container_ps', bound_used_container_ps)

        bound_used_container_ok_ps = self._newPS('return container.id')
        open._setOb('bound_used_container_ok_ps', bound_used_container_ok_ps)

        bound_unused_context_ps = self._newPS('return 1')
        guarded._setOb('bound_unused_context_ps', bound_unused_context_ps)

        bound_used_context_ps = self._newPS('return context.id')
        guarded._setOb('bound_used_context_ps', bound_used_context_ps)

        bound_used_context_methodWithRoles_ps = self._newPS(
            'return context.methodWithRoles()')
        guarded._setOb('bound_used_context_methodWithRoles_ps',
                       bound_used_context_methodWithRoles_ps)

        container_ps = self._newPS('return container')
        guarded._setOb('container_ps', container_ps)

        container_str_ps = self._newPS('return str(container)')
        guarded._setOb('container_str_ps', container_str_ps)

        context_ps = self._newPS('return context')
        guarded._setOb('context_ps', context_ps)

        context_str_ps = self._newPS('return str(context)')
        guarded._setOb('context_str_ps', context_str_ps)

        return root

    def _newPS(self, txt, bind=None):
        from Products.PythonScripts.PythonScript import PythonScript
        ps = PythonScript('ps')
        ps.write(txt)
        ps._makeFunction()
        return ps

    # These test that the mere binding of context or container, when the
    # user doesn't have access to them, doesn't raise an unauthorized. An
    # exception *will* be raised if the script attempts to use them. This
    # is a b/w compatibility hack: see Bindings.py for details.

    def test_bound_unused_container(self):
        from AccessControl.SecurityManagement import newSecurityManager
        newSecurityManager(None, UnderprivilegedUser())
        root = self._makeTree()
        guarded = root._getOb('guarded')
        ps = guarded._getOb('bound_unused_container_ps')
        self.assertEqual(ps(), 1)

    def test_bound_used_container(self):
        from AccessControl import Unauthorized
        from AccessControl.SecurityManagement import newSecurityManager
        newSecurityManager(None, UnderprivilegedUser())
        root = self._makeTree()
        guarded = root._getOb('guarded')

        ps = guarded._getOb('bound_used_container_ps')
        self.assertRaises(Unauthorized, ps)

        ps = guarded._getOb('container_str_ps')
        self.assertRaises(Unauthorized, ps)

        ps = guarded._getOb('container_ps')
        container = ps()

        with self.assertRaises(Unauthorized):
            container()

        self.assertRaises(Unauthorized, container.index_html)
        try:
            str(container)
        except Unauthorized:
            pass
        else:
            self.fail("str(container) didn't raise Unauthorized!")

        ps = guarded._getOb('bound_used_container_ps')
        ps._proxy_roles = ('Manager', )
        ps()

        ps = guarded._getOb('container_str_ps')
        ps._proxy_roles = ('Manager', )
        ps()

    def test_bound_used_container_allowed(self):
        from AccessControl.SecurityManagement import newSecurityManager
        newSecurityManager(None, UnderprivilegedUser())
        root = self._makeTree()
        guarded = root._getOb('guarded')
        open = guarded._getOb('open')
        ps = open.unrestrictedTraverse('bound_used_container_ok_ps')
        self.assertEqual(ps(), 'open')

    def test_bound_unused_context(self):
        from AccessControl.SecurityManagement import newSecurityManager
        newSecurityManager(None, UnderprivilegedUser())
        root = self._makeTree()
        guarded = root._getOb('guarded')
        ps = guarded._getOb('bound_unused_context_ps')
        self.assertEqual(ps(), 1)

    def test_bound_used_context(self):
        from AccessControl import Unauthorized
        from AccessControl.SecurityManagement import newSecurityManager
        newSecurityManager(None, UnderprivilegedUser())
        root = self._makeTree()
        guarded = root._getOb('guarded')

        ps = guarded._getOb('bound_used_context_ps')
        self.assertRaises(Unauthorized, ps)

        ps = guarded._getOb('context_str_ps')
        self.assertRaises(Unauthorized, ps)

        ps = guarded._getOb('context_ps')
        context = ps()

        # Without using the contextmanager 'assertRaises' tries to access an
        # attribute of context, which leads to an error right away.
        with self.assertRaises(Unauthorized):
            context()

        self.assertRaises(Unauthorized, context.index_html)
        try:
            str(context)
        except Unauthorized:
            pass
        else:
            self.fail("str(context) didn't raise Unauthorized!")

        ps = guarded._getOb('bound_used_context_ps')
        ps._proxy_roles = ('Manager', )
        ps()

        ps = guarded._getOb('context_str_ps')
        ps._proxy_roles = ('Manager', )
        ps()

    def test_bound_used_context_allowed(self):
        from AccessControl.SecurityManagement import newSecurityManager
        newSecurityManager(None, UnderprivilegedUser())
        root = self._makeTree()
        guarded = root._getOb('guarded')
        open = guarded._getOb('open')
        ps = open.unrestrictedTraverse('bound_used_context_ps')
        self.assertEqual(ps(), 'open')

    def test_ok_no_bindings(self):
        from AccessControl.SecurityManagement import newSecurityManager
        newSecurityManager(None, UnderprivilegedUser())
        root = self._makeTree()
        guarded = root._getOb('guarded')
        boundless_ps = self._newPS('return 42')
        guarded._setOb('boundless_ps', boundless_ps)
        boundless_ps = guarded._getOb('boundless_ps')
        # Clear the bindings, so that the script may execute.
        boundless_ps.ZBindings_edit({'name_context': '',
                                     'name_container': '',
                                     'name_m_self': '',
                                     'name_ns': '',
                                     'name_subpath': ''})
        self.assertEqual(boundless_ps(), 42)

    def test_bound_used_context_method_w_roles(self):
        from AccessControl import Unauthorized
        from AccessControl.SecurityManagement import newSecurityManager
        newSecurityManager(None, UnderprivilegedUser())
        root = self._makeTree()
        guarded = root._getOb('guarded')

        # Assert that we can call a protected method, even though we have
        # no access to the context directly.
        ps = guarded._getOb('bound_used_context_ps')
        self.assertRaises(Unauthorized, ps)
        ps = guarded._getOb('bound_used_context_methodWithRoles_ps')
        self.assertEqual(ps(), 'method called')
