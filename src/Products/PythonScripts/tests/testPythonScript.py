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
import codecs
import contextlib
import io
import os
import sys
import unittest
import warnings
from urllib.error import HTTPError

import zExceptions
import Zope2
from AccessControl.Permissions import change_proxy_roles
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import noSecurityManager
from OFS.Folder import Folder
from Testing.makerequest import makerequest
from Testing.testbrowser import Browser
from Testing.ZopeTestCase import FunctionalTestCase

from ..PythonScript import PythonScript


HERE = os.path.dirname(__file__)


@contextlib.contextmanager
def warning_interceptor():
    old_stderr = sys.stderr
    sys.stderr = stream = io.StringIO()
    try:
        yield stream
    finally:
        sys.stderr = old_stderr


# Test Classes


def readf(name):
    path = os.path.join(HERE, 'tscripts', '%s.ps' % name)
    with open(path) as f:
        return f.read()


class DummyFolder(Folder):
    """ Stitch in an implementation for getPhysicalPath """

    def getPhysicalPath(self):
        return ()


class PythonScriptTestBase(unittest.TestCase):

    def setUp(self):
        from AccessControl import ModuleSecurityInfo
        from AccessControl.SecurityInfo import _appliedModuleSecurity
        from AccessControl.SecurityInfo import _moduleSecurity
        self._ms_before = _moduleSecurity.copy()
        self._ams_before = _appliedModuleSecurity.copy()
        ModuleSecurityInfo('string').declarePublic('split')  # noqa: D001
        ModuleSecurityInfo('sets').declarePublic('Set')  # noqa: D001
        newSecurityManager(None, None)

    def tearDown(self):
        from AccessControl.SecurityInfo import _appliedModuleSecurity
        from AccessControl.SecurityInfo import _moduleSecurity
        noSecurityManager()
        _moduleSecurity.clear()
        _moduleSecurity.update(self._ms_before)
        _appliedModuleSecurity.clear()
        _appliedModuleSecurity.update(self._ams_before)

    def _newPS(self, txt, bind=None):
        ps = PythonScript('ps')
        ps.ZBindings_edit(bind or {})
        ps.write(txt)
        ps._makeFunction()
        if ps.errors:
            raise SyntaxError(ps.errors[0])
        return ps

    def _filePS(self, fname, bind=None):
        ps = PythonScript(fname)
        ps.ZBindings_edit(bind or {})
        ps.write(readf(fname))
        ps._makeFunction()
        if ps.errors:
            raise SyntaxError(ps.errors[0])
        return ps


class TestPythonScriptNoAq(PythonScriptTestBase):

    def testEmpty(self):
        empty = self._newPS('')()
        self.assertIsNone(empty)

    def testIndented(self):
        # This failed to compile in Zope 2.4.0b2.
        res = self._newPS('if 1:\n return 2')()
        self.assertEqual(res, 2)

    def testReturn(self):
        res = self._newPS('return 1')()
        self.assertEqual(res, 1)

    def testReturnNone(self):
        res = self._newPS('return')()
        self.assertIsNone(res)

    def testParam1(self):
        res = self._newPS('##parameters=x\nreturn x')('txt')
        self.assertEqual(res, 'txt')

    def testParam2(self):
        eq = self.assertEqual
        one, two = self._newPS('##parameters=x,y\nreturn x,y')('one', 'two')
        eq(one, 'one')
        eq(two, 'two')

    def testParam26(self):
        import string
        params = string.ascii_letters[:26]
        sparams = ','.join(params)
        ps = self._newPS(f'##parameters={sparams}\nreturn {sparams}')
        res = ps(*params)
        self.assertEqual(res, tuple(params))

    def testArithmetic(self):
        res = self._newPS('return 1 * 5 + 4 / 2 - 6')()
        self.assertEqual(res, 1)

    def testReduce(self):
        res = self._newPS('return reduce(lambda x, y: x + y, [1,3,5,7])')()
        self.assertEqual(res, 16)
        res = self._newPS('return reduce(lambda x, y: x + y, [1,3,5,7], 1)')()
        self.assertEqual(res, 17)

    def testImport(self):
        res = self._newPS('import string; return "7" in string.digits')()
        self.assertTrue(res)

    def testWhileLoop(self):
        res = self._filePS('while_loop')()
        self.assertEqual(res, 1)

    def testForLoop(self):
        res = self._filePS('for_loop')()
        self.assertEqual(res, 10)

    def testMutateLiterals(self):
        eq = self.assertEqual
        l, d = self._filePS('mutate_literals')()
        eq(l, [2])
        eq(d, {'b': 2})

    def testTupleUnpackAssignment(self):
        eq = self.assertEqual
        d, x = self._filePS('tuple_unpack_assignment')()
        eq(d, {'a': 0, 'b': 1, 'c': 2})
        eq(x, 3)

    def testDoubleNegation(self):
        res = self._newPS('return not not "this"')()
        self.assertEqual(res, 1)

    def testTryExcept(self):
        eq = self.assertEqual
        a, b = self._filePS('try_except')()
        eq(a, 1)
        eq(b, 1)

    def testBigBoolean(self):
        res = self._filePS('big_boolean')()
        self.assertTrue(res)

    def testFibonacci(self):
        res = self._filePS('fibonacci')()
        self.assertEqual(
            res, [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377,
                  610, 987, 1597, 2584, 4181, 6765, 10946, 17711, 28657,
                  46368, 75025, 121393, 196418, 317811, 514229, 832040,
                  1346269, 2178309, 3524578, 5702887, 9227465, 14930352,
                  24157817, 39088169, 63245986])

    def testSimplePrint(self):
        res = self._filePS('simple_print')()
        self.assertEqual(res, 'a\n')

    def testComplexPrint(self):
        res = self._filePS('complex_print')()
        self.assertEqual(res, 'double\ndouble\nx: 1\ny: 0 1 2\n\n')

    def testNSBind(self):
        f = self._filePS('ns_bind', bind={'name_ns': '_'})
        bound = f.__render_with_namespace__({'yes': 1, 'no': self.fail})
        self.assertEqual(bound, 1)

    def testNSBindInvalidHeader(self):
        self.assertRaises(SyntaxError, self._filePS, 'ns_bind_invalid')

    def testBooleanMap(self):
        res = self._filePS('boolean_map')()
        self.assertTrue(res)

    def testGetSize(self):
        f = self._filePS('complex_print')
        self.assertEqual(f.get_size(), len(f.read()))

    def testBuiltinSet(self):
        res = self._newPS('return len(set([1, 2, 3, 1]))')()
        self.assertEqual(res, 3)

    def testDateTime(self):
        res = self._newPS(
            "return DateTime('2007/12/10').strftime('%d.%m.%Y')")()
        self.assertEqual(res, '10.12.2007')

    def testRaiseSystemExitLaunchpad257269(self):
        ps = self._newPS('raise SystemExit')
        self.assertRaises(ValueError, ps)

    def testEncodingTestDotTestAllLaunchpad257276(self):
        ps = self._newPS("return 'foo'.encode('test.testall')")
        self.assertRaises(LookupError, ps)

    def test_manage_DAVget(self):
        ps = makerequest(self._filePS('complete'))
        self.assertEqual(ps.read(), ps.manage_DAVget())

    def test_PUT_native_string(self):
        ps = makerequest(self._filePS('complete'))
        self.assertEqual(ps.title, 'This is a title')
        self.assertEqual(ps.body(), 'print(foo+bar+baz)\nreturn printed\n')
        self.assertEqual(ps.params(), 'foo, bar, baz=1')
        new_body = """\
## Script (Python) "complete"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=oops
##title=New Title
##
return \xe4\xe9\xee\xf6\xfc
"""
        ps.REQUEST['BODY'] = new_body
        ps._filepath = 'fake'
        ps.PUT(ps.REQUEST, ps.REQUEST.RESPONSE)
        self.assertEqual(ps.title, 'New Title')
        self.assertEqual(ps.body(), 'return \xe4\xe9\xee\xf6\xfc\n')
        self.assertEqual(ps.params(), 'oops')

    def test_PUT_bytes(self):
        ps = makerequest(self._filePS('complete'))
        self.assertEqual(ps.title, 'This is a title')
        self.assertEqual(ps.body(), 'print(foo+bar+baz)\nreturn printed\n')
        self.assertEqual(ps.params(), 'foo, bar, baz=1')
        new_body = b"""\
## Script (Python) "complete"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=oops
##title=New Title
##
return \xc3\xa4\xc3\xa9\xc3\xae\xc3\xb6\xc3\xbc
"""
        ps.REQUEST['BODY'] = new_body
        ps._filepath = 'fake'
        ps.PUT(ps.REQUEST, ps.REQUEST.RESPONSE)
        self.assertEqual(ps.title, 'New Title')
        self.assertEqual(ps.body(), 'return \xe4\xe9\xee\xf6\xfc\n')
        self.assertEqual(ps.params(), 'oops')

    def test_write(self):
        ps = self._newPS('')

        ps.write(b'return 1')
        self.assertEqual(ps.body(), 'return 1\n')

        ps.write('return 1')
        self.assertEqual(ps.body(), 'return 1\n')

    def test_factory(self):
        from Products.PythonScripts.PythonScript import manage_addPythonScript

        # Only passing the id
        container = DummyFolder('container')
        manage_addPythonScript(container, 'testing')
        self.assertEqual(container.testing.getId(), 'testing')
        self.assertEqual(container.testing.title, '')
        self.assertIn('# Example code:', container.testing.body())
        self.assertEqual(container.testing.params(), '')

        # Passing id and a title
        container = DummyFolder('container')
        manage_addPythonScript(container, 'testing', title='This is a title')
        self.assertEqual(container.testing.getId(), 'testing')
        self.assertEqual(container.testing.title, 'This is a title')
        self.assertIn('# Example code:', container.testing.body())
        self.assertEqual(container.testing.params(), '')

        # Passing id, title and a request that has no file
        container = makerequest(DummyFolder('container'))
        container.REQUEST.form = {}
        manage_addPythonScript(container, 'testing', title='This is a title',
                               REQUEST=container.REQUEST)
        self.assertEqual(container.testing.getId(), 'testing')
        self.assertEqual(container.testing.title, 'This is a title')
        self.assertIn('# Example code:', container.testing.body())
        self.assertEqual(container.testing.params(), '')

        # Passing id, title and a request ith a file string
        container = makerequest(DummyFolder('container'))
        container.REQUEST.form = {'file': 'return 1'}
        manage_addPythonScript(container, 'testing', title='This is a title',
                               REQUEST=container.REQUEST)
        self.assertEqual(container.testing.getId(), 'testing')
        self.assertEqual(container.testing.title, 'This is a title')
        self.assertEqual(container.testing.body(), 'return 1\n')
        self.assertEqual(container.testing.params(), '')

        # Passing id, title and a request with a file object
        container = makerequest(DummyFolder('container'))
        container.REQUEST.form = {'file': io.BytesIO(b'return 1')}
        manage_addPythonScript(container, 'testing', title='This is a title',
                               REQUEST=container.REQUEST)
        self.assertEqual(container.testing.getId(), 'testing')
        self.assertEqual(container.testing.title, 'This is a title')
        self.assertEqual(container.testing.body(), 'return 1\n')
        self.assertEqual(container.testing.params(), '')

        # Passing id, title and a file string
        container = makerequest(DummyFolder('container'))
        manage_addPythonScript(container, 'testing', title='This is a title',
                               file=b'return 1')
        self.assertEqual(container.testing.getId(), 'testing')
        self.assertEqual(container.testing.title, 'This is a title')
        self.assertEqual(container.testing.body(), 'return 1\n')
        self.assertEqual(container.testing.params(), '')

        # Passing id, title and a file object
        container = makerequest(DummyFolder('container'))
        manage_addPythonScript(container, 'testing', title='This is a title',
                               file=io.BytesIO(b'return 1'))
        self.assertEqual(container.testing.getId(), 'testing')
        self.assertEqual(container.testing.title, 'This is a title')
        self.assertEqual(container.testing.body(), 'return 1\n')
        self.assertEqual(container.testing.params(), '')

    def testCodeIntrospection(self):
        script = self._newPS('##parameters=a="b"')

        self.assertEqual(script.__code__.co_argcount, 1)
        self.assertEqual(
            script.__code__.co_varnames,
            ('a',))
        self.assertEqual(script.__defaults__, ('b',))


class TestPythonScriptErrors(PythonScriptTestBase):

    def assertPSRaises(self, error, path=None, body=None):
        assert not (path and body) and (path or body)
        if body is None:
            body = readf(path)
        if error is SyntaxError:
            self.assertRaises(SyntaxError, self._newPS, body)
        else:
            ps = self._newPS(body)
            self.assertRaises(error, ps)

    def testSubversiveExcept(self):
        self.assertPSRaises(SyntaxError, path='subversive_except')

    def testBadImports(self):
        from zExceptions import Unauthorized
        self.assertPSRaises(SyntaxError, body='from string import *')
        self.assertPSRaises(Unauthorized, body='from datetime import datetime')
        self.assertPSRaises(Unauthorized, body='import mmap')

    def testAttributeAssignment(self):
        # It's illegal to assign to attributes of anything that
        # doesn't have enabling security declared.
        # Classes (and their instances) defined by restricted code
        # are an exception -- they are fully readable and writable.
        cases = [('import string', 'string'),
                 ('def f(): pass', 'f'),
                 ]
        assigns = ["%s.splat = 'spam'",
                   "setattr(%s, '_getattr_', lambda x, y: True)",
                   'del %s.splat',
                   ]

        for defn, name in cases:
            for asn in assigns:
                func = self._newPS(defn + '\n' + asn % name)
                self.assertRaises(TypeError, func)

    def testBadIdentifiers(self):
        """Some identifiers have to be avoided.

        Background:
        https://github.com/zopefoundation/Zope/issues/669
        """
        bad_identifiers = [
            'context', 'container', 'script', 'traverse_subpath',
        ]
        for identifier in bad_identifiers:
            with self.assertRaises(ValueError):
                PythonScript(identifier)


class TestPythonScriptGlobals(PythonScriptTestBase):

    def setUp(self):
        PythonScriptTestBase.setUp(self)

    def tearDown(self):
        PythonScriptTestBase.tearDown(self)

    def _exec(self, script, bound_names=None, args=None, kws=None):
        if args is None:
            args = ()
        if kws is None:
            kws = {}
        bindings = {'name_container': 'container'}
        f = self._filePS(script, bindings)
        return f._exec(bound_names, args, kws)

    def testGlobalIsDeclaration(self):
        bindings = {'container': 7}
        results = self._exec('global_is_declaration', bindings)
        self.assertEqual(results, 8)

    def test__name__(self):
        f = self._filePS('class.__name__')
        class_name = "'script.class.__name__.<locals>.foo'>"

        self.assertEqual(f(), (class_name, "'string'"))

    def test_filepath(self):
        # This test is meant to raise a deprecation warning.
        # It used to fail mysteriously instead.
        def warnMe(message):
            warnings.warn(message, stacklevel=2)

        try:
            f = self._filePS('filepath')
            with warning_interceptor() as stream:
                f._exec({'container': warnMe}, (), {})
                self.assertIn('UserWarning: foo', stream.getvalue())
        except TypeError as e:
            self.fail(e)


class PythonScriptInterfaceConformanceTests(unittest.TestCase):

    def test_class_conforms_to_IWriteLock(self):
        from OFS.interfaces import IWriteLock
        from zope.interface.verify import verifyClass
        verifyClass(IWriteLock, PythonScript)


class PythonScriptBrowserTests(FunctionalTestCase):
    """Browser testing Python Scripts"""

    def setUp(self):
        from Products.PythonScripts.PythonScript import manage_addPythonScript
        super().setUp()

        Zope2.App.zcml.load_site(force=True)

        uf = self.app.acl_users
        uf.userFolderAddUser('manager', 'manager_pass', ['Manager'], [])
        manage_addPythonScript(self.app, 'py_script')

        self.browser = Browser()
        pw = codecs.encode(b'manager:manager_pass', 'base64').decode()
        self.browser.addHeader('Authorization', f'basic {pw}')
        self.browser.open('http://localhost/py_script/manage_main')

    def test_ZPythonScriptHTML_upload__no_file(self):
        """It renders an error message if no file is uploaded."""
        self.browser.getControl('Upload File').click()
        self.assertIn('No file specified', self.browser.contents)

    def test_ZPythonScriptHTML_upload__with_file(self):
        file_contents = b'print("hello")'
        self.browser.getControl('file').add_file(
            file_contents, 'text/plain', 'script.py')
        self.browser.getControl('Upload File').click()

        assert 'Saved changes.' in self.browser.contents

    def test_PythonScript_proxyroles_manager(self):
        test_role = 'Test Role'
        self.app._addRole(test_role)

        # Test the original state
        self.assertFalse(self.app.py_script.manage_haveProxy(test_role))

        # Go to the "Proxy" ZMI tab, grab the Proxy Roles select box,
        # select the new role and submit
        self.browser.open('http://localhost/py_script/manage_proxyForm')
        roles_selector = self.browser.getControl(name='roles:list')
        testrole_option = roles_selector.getControl(test_role)
        self.assertFalse(testrole_option.selected)
        testrole_option.selected = True
        self.browser.getControl('Save Changes').click()

        # The Python Script should now have a proxy role set
        self.assertTrue(self.app.py_script.manage_haveProxy(test_role))

    def test_PythonScript_proxyroles_nonmanager(self):
        # This test checks an unusual configuration where roles other than
        # Manager are allowed to change proxy roles.
        proxy_form_url = 'http://localhost/py_script/manage_proxyForm'
        test_role = 'Test Role'
        self.app._addRole(test_role)
        test_role_2 = 'Unprivileged Role'
        self.app._addRole(test_role_2)
        self.app.manage_permission(change_proxy_roles, ['Manager', test_role])

        # Add some test users
        uf = self.app.acl_users
        uf.userFolderAddUser('privileged', 'priv', [test_role], [])
        uf.userFolderAddUser('peon', 'unpriv', [test_role_2], [])

        # Test the original state
        self.assertFalse(self.app.py_script.manage_haveProxy(test_role))
        self.assertFalse(self.app.py_script.manage_haveProxy(test_role_2))

        # Attempt as unprivileged user will fail both in the browser and
        # from trusted code
        self.browser.login('peon', 'unpriv')
        with self.assertRaises(HTTPError):
            self.browser.open(proxy_form_url)

        newSecurityManager(None, uf.getUser('peon'))
        with self.assertRaises(zExceptions.Forbidden):
            self.app.py_script.manage_proxy(roles=(test_role,))
        self.assertFalse(self.app.py_script.manage_haveProxy(test_role))

        # Now log in as privileged user and try to set a proxy role
        # the privileged user does not have. This must fail.
        self.browser.login('privileged', 'priv')
        self.browser.open(proxy_form_url)
        roles_selector = self.browser.getControl(name='roles:list')
        bad_option = roles_selector.getControl(test_role_2)
        self.assertFalse(bad_option.selected)
        bad_option.selected = True
        with self.assertRaises(HTTPError):
            self.browser.getControl('Save Changes').click()
        self.assertFalse(self.app.py_script.manage_haveProxy(test_role_2))

        newSecurityManager(None, uf.getUser('privileged'))
        with self.assertRaises(zExceptions.Forbidden):
            self.app.py_script.manage_proxy(roles=(test_role_2,))
        self.assertFalse(self.app.py_script.manage_haveProxy(test_role_2))

        # Trying again as privileged user with a proxy role the user has
        self.browser.open(proxy_form_url)
        roles_selector = self.browser.getControl(name='roles:list')
        testrole_option = roles_selector.getControl(test_role)
        self.assertFalse(testrole_option.selected)
        testrole_option.selected = True
        self.browser.getControl('Save Changes').click()

        # The Python Script should now have a proxy role set
        self.assertTrue(self.app.py_script.manage_haveProxy(test_role))

        # Cleanup
        noSecurityManager()
