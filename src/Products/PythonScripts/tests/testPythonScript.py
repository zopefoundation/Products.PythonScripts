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
import contextlib
import os
import six
import sys
import unittest
import warnings

from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import noSecurityManager

from Products.PythonScripts.PythonScript import PythonScript


HERE = os.path.dirname(__file__)


@contextlib.contextmanager
def warning_interceptor():
    old_stderr = sys.stderr
    sys.stderr = stream = six.StringIO()
    try:
        yield stream
    finally:
        sys.stderr = old_stderr


# Test Classes


def readf(name):
    path = os.path.join(HERE, 'tscripts', '%s.ps' % name)
    return open(path, 'r').read()


class PythonScriptTestBase(unittest.TestCase):

    def setUp(self):
        from AccessControl import ModuleSecurityInfo
        from AccessControl.SecurityInfo import _moduleSecurity
        from AccessControl.SecurityInfo import _appliedModuleSecurity
        self._ms_before = _moduleSecurity.copy()
        self._ams_before = _appliedModuleSecurity.copy()
        ModuleSecurityInfo('string').declarePublic('split')
        ModuleSecurityInfo('sets').declarePublic('Set')
        newSecurityManager(None, None)

    def tearDown(self):
        from AccessControl.SecurityInfo import _moduleSecurity
        from AccessControl.SecurityInfo import _appliedModuleSecurity
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
        self.failUnless(empty is None)

    def testIndented(self):
        # This failed to compile in Zope 2.4.0b2.
        res = self._newPS('if 1:\n return 2')()
        self.assertEqual(res, 2)

    def testReturn(self):
        res = self._newPS('return 1')()
        self.assertEqual(res, 1)

    def testReturnNone(self):
        res = self._newPS('return')()
        self.failUnless(res is None)

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
        ps = self._newPS('##parameters=%s\nreturn %s' % (sparams, sparams))
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
        self.failUnless(res)

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
        script = 'complex_print_py%s' % sys.version_info.major
        res = self._filePS(script)()
        self.assertEqual(res, 'double\ndouble\nx: 1\ny: 0 1 2\n\n')

    def testNSBind(self):
        f = self._filePS('ns_bind', bind={'name_ns': '_'})
        bound = f.__render_with_namespace__({'yes': 1, 'no': self.fail})
        self.assertEqual(bound, 1)

    def testNSBindInvalidHeader(self):
        self.assertRaises(SyntaxError, self._filePS, 'ns_bind_invalid')

    def testBooleanMap(self):
        res = self._filePS('boolean_map')()
        self.failUnless(res)

    def testGetSize(self):
        script = 'complex_print_py%s' % sys.version_info.major
        f = self._filePS(script)
        self.assertEqual(f.get_size(), len(f.read()))

    def testBuiltinSet(self):
        res = self._newPS('return len(set([1, 2, 3, 1]))')()
        self.assertEqual(res, 3)

    @unittest.skipIf(six.PY3, 'sets module does not exist in python3')
    def testSetModule(self):
        res = self._newPS('from sets import Set; return len(Set([1,2,3]))')()
        self.assertEqual(res, 3)

    def testDateTime(self):
        res = self._newPS(
            "return DateTime('2007/12/10').strftime('%d.%m.%Y')")()
        self.assertEqual(res, '10.12.2007')

    def testRaiseSystemExitLaunchpad257269(self):
        ps = self._newPS("raise SystemExit")
        self.assertRaises(ValueError, ps)

    def testEncodingTestDotTestAllLaunchpad257276(self):
        ps = self._newPS("return 'foo'.encode('test.testall')")
        self.assertRaises(LookupError, ps)


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
        if six.PY2:
            self.assertPSRaises(Unauthorized, body="from string import *")

        if six.PY3:
            with self.assertRaises(SyntaxError):
                self.assertPSRaises(Unauthorized, body="from string import *")

        self.assertPSRaises(Unauthorized, body="from datetime import datetime")
        self.assertPSRaises(Unauthorized, body="import mmap")

    def testAttributeAssignment(self):
        # It's illegal to assign to attributes of anything that
        # doesn't have enabling security declared.
        # Classes (and their instances) defined by restricted code
        # are an exception -- they are fully readable and writable.
        cases = [("import string", "string"),
                 ("def f(): pass", "f"),
                 ]
        assigns = ["%s.splat = 'spam'",
                   "setattr(%s, '_getattr_', lambda x, y: True)",
                   "del %s.splat",
                   ]

        for defn, name in cases:
            for asn in assigns:
                func = self._newPS(defn + "\n" + asn % name)
                self.assertRaises(TypeError, func)


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
        if six.PY3:
            class_name = "'script.class.__name__.<locals>.foo'>"
        else:
            class_name = "'script.foo'>"

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
                self.failUnless('UserWarning: foo' in stream.getvalue())
        except TypeError as e:
            self.fail(e)


class PythonScriptInterfaceConformanceTests(unittest.TestCase):

    def test_class_conforms_to_IWriteLock(self):
        from zope.interface.verify import verifyClass
        try:
            from OFS.interfaces import IWriteLock
        except ImportError:
            from webdav.interfaces import IWriteLock
        verifyClass(IWriteLock, PythonScript)
