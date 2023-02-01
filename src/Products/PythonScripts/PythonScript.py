##############################################################################
#
# Copyright (c) 2002 Zope Foundation and Contributors.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Python Scripts Product

This product provides support for Script objects containing restricted
Python code.
"""

import importlib.util
import marshal
import os
import re
import sys
import types
from logging import getLogger
from urllib.parse import quote

from AccessControl.class_init import InitializeClass
from AccessControl.Permissions import change_proxy_roles
from AccessControl.Permissions import change_python_scripts
from AccessControl.Permissions import view_management_screens
from AccessControl.requestmethod import requestmethod
from AccessControl.SecurityInfo import ClassSecurityInfo
from AccessControl.SecurityManagement import getSecurityManager
from AccessControl.ZopeGuards import get_safe_globals
from AccessControl.ZopeGuards import guarded_getattr
from Acquisition import aq_parent
from App.Common import package_home
from App.special_dtml import DTMLFile
from OFS.Cache import Cacheable
from OFS.History import Historical
from OFS.History import html_diff
from OFS.SimpleItem import SimpleItem
from RestrictedPython import compile_restricted_function
from Shared.DC.Scripts.Script import BindingsUI
from Shared.DC.Scripts.Script import Script
from Shared.DC.Scripts.Script import defaultBindings
from zExceptions import Forbidden
from zExceptions import ResourceLockedError
from ZPublisher.HTTPRequest import default_encoding


LOG = getLogger('PythonScripts')

# Track the Python bytecode version
Python_magic = importlib.util.MAGIC_NUMBER

# This should only be incremented to force recompilation.
Script_magic = 4
_log_complaint = (
    'Some of your Scripts have stale code cached.  Since Zope cannot'
    ' use this code, startup will be slightly slower until these Scripts'
    ' are edited. You can automatically recompile all Scripts that have'
    ' this problem by visiting /manage_addProduct/PythonScripts/recompile'
    ' of your server in a browser.')
manage_addPythonScriptForm = DTMLFile('www/pyScriptAdd', globals())
_default_file = os.path.join(package_home(globals()), 'www', 'default_content')
_marker = []  # Create a new marker object


def manage_addPythonScript(self, id, title='', file=None, REQUEST=None,
                           submit=None):
    """Add a Python script to a folder.
    """
    id = str(id)
    id = self._setObject(id, PythonScript(id))
    pyscript = self._getOb(id)
    if title:
        pyscript.ZPythonScript_setTitle(title)

    file = file or (REQUEST and REQUEST.form.get('file'))
    if hasattr(file, 'read'):
        file = file.read()
    if not file:
        with open(_default_file) as fp:
            file = fp.read()
    pyscript.write(file)

    if REQUEST is not None:
        try:
            u = self.DestinationURL()
        except Exception:
            u = REQUEST['URL1']
        if submit == 'Add and Edit':
            u = f'{u}/{quote(id)}'
        REQUEST.RESPONSE.redirect(u + '/manage_main')
    return ''


class PythonScript(Script, Historical, Cacheable):
    """Web-callable scripts written in a safe subset of Python.

    The function may include standard python code, so long as it does
    not attempt to use the "exec" statement or certain restricted builtins.
    """

    meta_type = 'Script (Python)'
    zmi_icon = 'fa fa-terminal'
    _proxy_roles = ()

    _params = _body = ''
    errors = warnings = ()
    _v_change = 0

    manage_options = (
        {'label': 'Edit', 'action': 'ZPythonScriptHTML_editForm'},
    ) + BindingsUI.manage_options + (
        {'label': 'Test', 'action': 'ZScriptHTML_tryForm'},
        {'label': 'Proxy', 'action': 'manage_proxyForm'},
    ) + Historical.manage_options + SimpleItem.manage_options + \
        Cacheable.manage_options

    def __init__(self, id):
        self.ZBindings_edit(defaultBindings)
        bind_names = self.getBindingAssignments().getAssignedNamesInOrder()
        if id in bind_names:
            raise ValueError(
                'Following names are not allowed as identifiers, as they'
                'have a special meaning for PythonScript: '
                '%s.'
                'Please choose another name.' % ', '.join(bind_names))
        self.id = id
        self._makeFunction()

    security = ClassSecurityInfo()

    security.declareObjectProtected('View')
    security.declareProtected('View', '__call__')  # noqa: D001

    security.declareProtected(  # noqa: D001
        view_management_screens,
        'ZPythonScriptHTML_editForm', 'manage_main', 'ZScriptHTML_tryForm')

    ZPythonScriptHTML_editForm = DTMLFile('www/pyScriptEdit', globals())
    manage = manage_main = ZPythonScriptHTML_editForm
    ZPythonScriptHTML_editForm._setName('ZPythonScriptHTML_editForm')

    @security.protected(change_python_scripts)
    def ZPythonScriptHTML_editAction(self, REQUEST, title, params, body):
        """Change the script's main parameters."""
        self.ZPythonScript_setTitle(title)
        self.ZPythonScript_edit(params, body)
        message = 'Saved changes.'
        return self.ZPythonScriptHTML_editForm(self, REQUEST,
                                               manage_tabs_message=message)

    @security.protected(change_python_scripts)
    def ZPythonScript_setTitle(self, title):
        title = str(title)
        if self.title != title:
            self.title = title
            self.ZCacheable_invalidate()

    @security.protected(change_python_scripts)
    def ZPythonScript_edit(self, params, body):
        self._validateProxy()
        if self.wl_isLocked():
            raise ResourceLockedError('The script is locked via WebDAV.')
        if not isinstance(body, str):
            body = body.read()

        if self._params != params or self._body != body or self._v_change:
            self._params = str(params)
            self.write(body)

    @security.protected(change_python_scripts)
    def ZPythonScriptHTML_upload(self, REQUEST, file=''):
        """Replace the body of the script with the text in file."""
        if self.wl_isLocked():
            raise ResourceLockedError('The script is locked via WebDAV.')

        if not isinstance(file, str):
            if not file:
                return self.ZPythonScriptHTML_editForm(
                    self, REQUEST,
                    manage_tabs_message='No file specified',
                    manage_tabs_type='warning')
            file = file.read()

        self.write(file)
        message = 'Saved changes.'
        return self.ZPythonScriptHTML_editForm(self, REQUEST,
                                               manage_tabs_message=message)

    def ZScriptHTML_tryParams(self):
        """Parameters to test the script with."""
        param_names = []
        for name in self._params.split(','):

            name = name.strip()
            if name and name[0] != '*' and re.match(r'\w', name):
                param_names.append(name.split('=', 1)[0].strip())
        return param_names

    @security.protected(view_management_screens)
    def manage_historyCompare(self, rev1, rev2, REQUEST,
                              historyComparisonResults=''):
        return PythonScript.inheritedAttribute('manage_historyCompare')(
            self, rev1, rev2, REQUEST,
            historyComparisonResults=html_diff(rev1.read(), rev2.read()))

    def __setstate__(self, state):
        Script.__setstate__(self, state)
        if getattr(self, 'Python_magic', None) != Python_magic or \
           getattr(self, 'Script_magic', None) != Script_magic:
            global _log_complaint
            if _log_complaint:
                LOG.info(_log_complaint)
                _log_complaint = 0
            # Changes here won't get saved, unless this Script is edited.
            body = self._body.rstrip()
            if body:
                self._body = body + '\n'
            self._compile()
            self._v_change = 1
        elif self._code is None:
            self._v_ft = None
        else:
            self._newfun(marshal.loads(self._code))

    def _compile(self):
        bind_names = self.getBindingAssignments().getAssignedNamesInOrder()
        compile_result = compile_restricted_function(
            self._params,
            body=self._body or 'pass',
            name=self.id,
            filename=self.meta_type,
            globalize=bind_names)

        code = compile_result.code
        errors = compile_result.errors
        self.warnings = tuple(compile_result.warnings)
        if errors:
            self._code = None
            self._v_ft = None
            self._setFuncSignature((), (), 0)
            # Fix up syntax errors.
            filestring = '  File "<string>",'
            for i in range(len(errors)):
                line = errors[i]
                if line.startswith(filestring):
                    errors[i] = line.replace(filestring, '  Script', 1)
            self.errors = errors
            return

        self._code = marshal.dumps(code)
        self.errors = ()
        f = self._newfun(code)
        fc = f.__code__
        self._setFuncSignature(f.__defaults__, fc.co_varnames,
                               fc.co_argcount)
        self.Python_magic = Python_magic
        self.Script_magic = Script_magic
        self._v_change = 0

    def _newfun(self, code):
        safe_globals = get_safe_globals()
        safe_globals['_getattr_'] = guarded_getattr
        safe_globals['__debug__'] = __debug__
        # it doesn't really matter what __name__ is, *but*
        # - we need a __name__
        #   (see testPythonScript.TestPythonScriptGlobals.test__name__)
        # - it should not contain a period, so we can't use the id
        #   (see https://bugs.launchpad.net/zope2/+bug/142731/comments/4)
        # - with Python 2.6 it should not be None
        #   (see testPythonScript.TestPythonScriptGlobals.test_filepath)
        safe_globals['__name__'] = 'script'

        safe_locals = {}
        exec(code, safe_globals, safe_locals)
        func = list(safe_locals.values())[0]
        self._v_ft = (func.__code__, safe_globals, func.__defaults__ or ())
        return func

    def _makeFunction(self):
        self.ZCacheable_invalidate()
        self._compile()
        if not (aq_parent(self) is None or hasattr(self, '_filepath')):
            # It needs a _filepath, and has an acquisition wrapper.
            self._filepath = self.get_filepath()

    def _editedBindings(self):
        if getattr(self, '_v_ft', None) is not None:
            self._makeFunction()

    def _exec(self, bound_names, args, kw):
        """Call a Python Script

        Calling a Python Script is an actual function invocation.
        """
        # Retrieve the value from the cache.
        keyset = None
        if self.ZCacheable_isCachingEnabled():
            # Prepare a cache key.
            keyset = kw.copy()
            asgns = self.getBindingAssignments()
            name_context = asgns.getAssignedName('name_context', None)
            if name_context:
                keyset[name_context] = aq_parent(self).getPhysicalPath()
            name_subpath = asgns.getAssignedName('name_subpath', None)
            if name_subpath:
                keyset[name_subpath] = self._getTraverseSubpath()
            # Note: perhaps we should cache based on name_ns also.
            keyset['*'] = args
            result = self.ZCacheable_get(keywords=keyset, default=_marker)
            if result is not _marker:
                # Got a cached value.
                return result

        ft = self._v_ft
        if ft is None:
            __traceback_supplement__ = (
                PythonScriptTracebackSupplement, self)
            raise RuntimeError(f'{self.meta_type} {self.id} has errors.')

        function_code, safe_globals, function_argument_definitions = ft
        safe_globals = safe_globals.copy()
        if bound_names is not None:
            safe_globals.update(bound_names)
        safe_globals['__traceback_supplement__'] = (
            PythonScriptTracebackSupplement, self, -1)
        safe_globals['__file__'] = getattr(
            self, '_filepath', None) or self.get_filepath()
        function = types.FunctionType(
            function_code, safe_globals, None, function_argument_definitions)

        try:
            result = function(*args, **kw)
        except SystemExit:
            raise ValueError(
                'SystemExit cannot be raised within a PythonScript')

        if keyset is not None:
            # Store the result in the cache.
            self.ZCacheable_set(result, keywords=keyset)
        return result

    def manage_afterAdd(self, item, container):
        if item is self:
            self._filepath = self.get_filepath()

    def manage_beforeDelete(self, item, container):
        # shut up deprecation warnings
        pass

    def manage_afterClone(self, item):
        # shut up deprecation warnings
        pass

    @security.protected(view_management_screens)
    def get_filepath(self):
        return self.meta_type + ':' + '/'.join(self.getPhysicalPath())

    def manage_haveProxy(self, r):
        return r in self._proxy_roles

    def _validateProxy(self, roles=None):
        if roles is None:
            roles = self._proxy_roles
        if not roles:
            return
        user = getSecurityManager().getUser()
        if user is not None and user.allowed(self, roles):
            return
        raise Forbidden(
            'You are not authorized to change <em>%s</em> '
            'because you do not have proxy roles.\n<!--%s, %s-->' % (
                self.id, user, roles))

    security.declareProtected(change_proxy_roles,  # NOQA: D001
                              'manage_proxyForm')

    manage_proxyForm = DTMLFile('www/pyScriptProxy', globals())

    @security.protected(change_proxy_roles)
    @requestmethod('POST')
    def manage_proxy(self, roles=(), REQUEST=None):
        """Change Proxy Roles"""
        user = getSecurityManager().getUser()
        if 'Manager' not in user.getRolesInContext(self):
            self._validateProxy(roles)
            self._validateProxy()
        self.ZCacheable_invalidate()
        self._proxy_roles = tuple(roles)
        if REQUEST:
            msg = 'Proxy roles changed.'
            return self.manage_proxyForm(manage_tabs_message=msg,
                                         management_view='Proxy')

    security.declareProtected(  # NOQA: D001
        change_python_scripts,
        'manage_FTPput', 'manage_historyCopy',
        'manage_beforeHistoryCopy', 'manage_afterHistoryCopy')

    @security.protected(change_python_scripts)
    def PUT(self, REQUEST, RESPONSE):
        """ Handle HTTP PUT requests """
        self.dav__init(REQUEST, RESPONSE)
        self.dav__simpleifhandler(REQUEST, RESPONSE, refresh=1)
        new_body = REQUEST.get('BODY', '')
        self.write(new_body)
        RESPONSE.setStatus(204)
        return RESPONSE

    manage_FTPput = PUT

    @security.protected(change_python_scripts)
    def write(self, text):
        """ Change the Script by parsing a read()-style source text. """
        self._validateProxy()
        mdata = self._metadata_map()
        bindmap = self.getBindingAssignments().getAssignedNames()
        bup = 0

        if isinstance(text, bytes):
            text = text.decode(default_encoding)

        st = 0
        try:
            while 1:
                # Find the next non-empty line
                m = _nonempty_line.search(text, st)
                if not m:
                    # There were no non-empty body lines
                    body = ''
                    break
                line = m.group(0).strip()
                if line[:2] != '##':
                    # We have found the first line of the body
                    body = text[m.start(0):]
                    break

                st = m.end(0)
                # Parse this header line
                if len(line) == 2 or line[2] == ' ' or '=' not in line:
                    # Null header line
                    continue
                k, v = line[2:].split('=', 1)
                k = k.strip().lower()
                v = v.strip()
                if k not in mdata:
                    raise SyntaxError('Unrecognized header line "%s"' % line)
                if v == mdata[k]:
                    # Unchanged value
                    continue

                # Set metadata value
                if k == 'title':
                    self.title = v
                elif k == 'parameters':
                    self._params = v
                elif k[:5] == 'bind ':
                    bindmap[_nice_bind_names[k[5:]]] = v
                    bup = 1

            body = body.rstrip()
            if body:
                body = body + '\n'
            if body != self._body:
                self._body = body
            if bup:
                self.ZBindings_edit(bindmap)
            else:
                self._makeFunction()
        except Exception:
            LOG.error('write failed', exc_info=sys.exc_info())
            raise

    def manage_DAVget(self):
        """Get source for WebDAV"""
        self.REQUEST.RESPONSE.setHeader('Content-Type', 'text/plain')
        return self.read()

    manage_FTPget = manage_DAVget

    def _metadata_map(self):
        m = {
            'title': self.title,
            'parameters': self._params,
        }
        bindmap = self.getBindingAssignments().getAssignedNames()
        for k, v in _nice_bind_names.items():
            m['bind ' + k] = bindmap.get(v, '')
        return m

    @security.protected(view_management_screens)
    def read(self):
        """ Generate a text representation of the Script source.

        Includes specially formatted comment lines for parameters,
        bindings, and the title.
        """
        # Construct metadata header lines, indented the same as the body.
        m = _first_indent.search(self._body)
        if m:
            prefix = m.group(0) + '##'
        else:
            prefix = '##'

        hlines = [f'{prefix} {self.meta_type} "{self.id}"']
        mm = sorted(self._metadata_map().items())
        for kv in mm:
            hlines.append('%s=%s' % kv)
        if self.errors:
            hlines.append('')
            hlines.append(' Errors:')
            for line in self.errors:
                hlines.append('  ' + line)
        if self.warnings:
            hlines.append('')
            hlines.append(' Warnings:')
            for line in self.warnings:
                hlines.append('  ' + line)
        hlines.append('')
        return ('\n' + prefix).join(hlines) + '\n' + self._body

    @security.protected(view_management_screens)
    def params(self):
        return self._params

    @security.protected(view_management_screens)
    def body(self):
        return self._body

    def get_size(self):
        return len(self.read())

    getSize = get_size

    @security.protected(view_management_screens)
    def PrincipiaSearchSource(self):
        """Support for searching - the document's contents are searched."""
        return f'{self._params}\n{self._body}'

    @security.protected(view_management_screens)
    def document_src(self, REQUEST=None, RESPONSE=None):
        """Return unprocessed document source."""

        if RESPONSE is not None:
            RESPONSE.setHeader('Content-Type', 'text/plain')
        return self.read()


InitializeClass(PythonScript)


class PythonScriptTracebackSupplement:
    """Implementation of ITracebackSupplement"""
    def __init__(self, script, line=0):
        self.object = script
        # If line is set to -1, it means to use tb_lineno.
        self.line = line


_first_indent = re.compile('(?m)^ *(?! |$)')
_nonempty_line = re.compile(r'(?m)^(.*\S.*)$')

_nice_bind_names = {'context': 'name_context', 'container': 'name_container',
                    'script': 'name_m_self', 'namespace': 'name_ns',
                    'subpath': 'name_subpath'}
