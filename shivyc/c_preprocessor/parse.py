from .tokens import Preproc
from .tokenize import PreprocToken

import re

"""
This is the parser for the C preprocessor.

Features supported:
    * Macros:
        #define VAR
        #define VAR VALUE
        #define FUNCTION(a, b, c) DO_STUFF_WITH(a, b, c)
        #undef VAR
    * File inclusion:
        #include <global>
        #include "local"
    * Errors and warnings:
        #error "This is an error!"
        #warning "Warning message"
    * Conditional execution:
        #if <expression, possibly including 'defined' and other macros>
        #ifdef MACRO
        #ifndef MACRO
        #elif <expression, possibly including 'defined' and other macros>
        #else
        #endif
    * Recognition and processing of non-preprocessor directives
    
TODO:
    * Concatenation:
        VAR1 ## VAR2
    * Stringification:
        #VAR
        
This might be buggy, so be warned.

PREPROCESSOR GRAMMAR USED HERE (in BNF; if a name does not appear on the right side of the ':=' sign, it's a terminal,
    whose definition is to be looked up in 'c_preprocessor.tokens'):
    
    control     := define_simple | define_value | define_function | undef | include_globl | include_local | error | warning | conditional
    conditional := if_str text elif_blocks else_block endif
    if_str      := if | ifdef | ifndef
    elif_blocks := elif text elif_blocks | empty
    else_block  := else text | empty
    text        := control text | c_code text | empty
    
Although the 'empty' symbol is defined in 'c_preprocessor.tokens', it does not actually appear in the token stream and is
    used as as a special symbol.
This grammar is LL(1).
"""

types = Preproc.Tok_types

class Code:
    indent_string = '  '

    def __init__(self, string: str, indent_level: int):
        self.code, self.indent_level = string, indent_level
        self.indentation = self.indent_string * indent_level

    def __str__(self):
        return ''.join(self.indentation + line for line in self.code.splitlines(keepends=True))


class Parser:
    """
    This is a predictive recursive descent parser that translates the preprocessor language to Python

    It parses through the token stream and generates equivalent Python code for each construct.
    """
    def __init__(self, file_path, tokens, First: dict, Follow: dict):
        """

        :param file_path: the path to the given file
        :param tokens: the tokens the contents of the file were tokenized into
        :param First: the first set for the above grammar
        :param Follow: the follow set for the above grammar
        """
        self.file_path = str(file_path)
        self.tokens = iter(tokens)

        self.pos, self.EOF = 0, False
        self.First, self.Follow = First, Follow

        self.code, self.indent_level = [], 0

        self._lookahead = next(self.tokens)

    def error(self, expected: set):
        expected = {e.name for e in expected}
        raise SyntaxError(f'Syntax error at line {self.lookahead.lineno} ({self.lookahead.value}):\n\texpected one of {expected}, got {self.lookahead}')

    @property
    def lookahead(self):
        if self.EOF:
            self._lookahead = PreprocToken(types.EOF, [''], self.pos)

        return self._lookahead

    def match(self, tok_type):
        if self.lookahead.type == tok_type:
            try:
                self._lookahead = next(self.tokens)
                self.pos += 1
            except:
                self.EOF = True

            return

        self.error({tok_type})

    def emit(self, code):
        self.code.append(Code(code, self.indent_level))

    def write_header(self):
        code = r'''
# these are to be passed later on
#
# substitute_variables(string, namespace: dict)
# include(file_name, search_paths)
#
# namespace, result = {}, []
# paths_global, paths_local = [], [] # for includes

GLOBALS = {
        '__builtin__': {'print': print},
        'namespace': namespace,
        'result': result,
        'paths_global': paths_global,
        'paths_local': paths_local,
        'substitute_variables': substitute_variables,
        'include': include,
        'get_value_by_name': get_value_by_name
        }
        
FILE_PATH = %s

def defined(name: str):
    return name in namespace
        ''' % repr(self.file_path)

        self.emit(code)

    def parse_define(self):
        name, *_ = self.lookahead.parse()

        if self.lookahead.type == types.define_simple:
            assert not _
            code = f'namespace[{name!r}] = ""'
        elif self.lookahead.type == types.define_value:
            assert len(_) == 1
            value = re.sub('([0-9]+)[UuLl]+', r'\1', _[0])  # remove suffixes

            try:
                value = int(eval(value, {}, {}))
                is_integer = True
            except:
                is_integer = False

            if not is_integer:
                code = f'namespace[{name!r}] = {value!r}'
            else:
                code = f'namespace[{name!r}] = {value}'

        elif self.lookahead.type == types.define_func:
            assert len(_) == 2
            args, value = _

            # since this is an actual function, return the desired result right away
            if '...' in args:
                args = args.split('...')[0] + '*variable'

                code = f'namespace[{name!r}] = lambda {args}: ""'
                code += '\nprint("WARNING: Variable number of arguments in function-like macros is not supported yet")'
            else:
                if args:
                    code = f'namespace[{name!r}] = lambda {args}: substitute_variables({value!r}, dict(zip((arg_name.strip() for arg_name in {args!r}.split(",")), ({args},))))'
                else:
                    code = f'namespace[{name!r}] = lambda : {value!r}'
        elif self.lookahead.type == types.undef:
            assert not _
            code = f'namespace.pop({name!r}, 0)'
        else:
            raise RuntimeError('This must not happen')

        self.emit(code)
        self.match(self.lookahead.type)

    def parse_include(self):
        file_name, *_ = self.lookahead.parse()
        assert not _

        if self.lookahead.type == types.include_globl:
            code = f'include({file_name!r}, paths_global, GLOBALS, FILE_PATH, local=False)'
        else:
            code = f'include({file_name!r}, paths_local, GLOBALS, FILE_PATH, local=True)'

        self.emit(code)
        self.match(self.lookahead.type)

    def parse_err(self):
        msg, *_ = self.lookahead.parse()
        assert not _

        if self.lookahead.type == types.error:
            code = f'raise RuntimeError({msg!r})'
        else:
            code = f'print("WARNING:", {msg!r})'

        self.emit(code)
        self.match(self.lookahead.type)

    def parse_control(self):
        define = {types.define_simple, types.define_value, types.define_func, types.undef}
        include = {types.include_globl, types.include_local}
        err = {types.warning, types.error}

        if self.lookahead.type in define:
            self.parse_define()
        elif self.lookahead.type in include:
            self.parse_include()
        elif self.lookahead.type in err:
            self.parse_err()
        elif self.lookahead.type in self.First['conditional']:
            self.parse_conditional()
        else:
            self.error(define | include | err | self.First['conditional'])

    def parse_conditional(self):
        self.parse_if_str()
        self.parse_text()
        self.parse_elif_blocks()
        self.parse_else_block()
        self.match(types.endif)

        self.indent_level -= 1

    def parse_if_str(self):
        if self.lookahead.type in self.First['if_str']:
            expr, *_ = self.lookahead.parse()
            assert len(_) == 0

            if self.lookahead.type == types.if_:
                code = f'if {expr}:'
            elif self.lookahead.type == types.ifdef:
                code = f'if defined({expr!r}):'
            elif self.lookahead.type == types.ifndef:
                code = f'if not defined({expr!r}):'
            else:
                raise RuntimeError('This must not happen!')

            self.emit(code)
            self.indent_level += 1

            self.match(self.lookahead.type)
        else:
            self.error(self.First['if_str'])

    def parse_elif_blocks(self):
        if self.lookahead.type in self.First['elif_blocks']:
            expr, *_ = self.lookahead.parse()
            assert len(_) == 0

            self.indent_level -= 1
            self.emit(f'elif {expr}:')
            self.indent_level += 1

            self.match(self.lookahead.type)
            self.parse_text()
            self.parse_elif_blocks()
        elif self.lookahead.type in self.Follow['elif_blocks']:
            ...
        else:
            self.error(self.First['elif_blocks'] | self.Follow['elif_blocks'])

    def parse_else_block(self):
        if self.lookahead.type in self.First['else_block']:
            self.indent_level -= 1
            self.emit('else:')
            self.indent_level += 1

            self.match(self.lookahead.type)
            self.parse_text()
        elif self.lookahead.type in self.Follow['else_block']:
            ...
        else:
            self.error(self.First['else_block'] | self.Follow['else_block'])

    def parse_text(self):
        c_code = {types.c_code}

        '''
        if self.lookahead.type in c_code:
            value, *_ = self.lookahead.parse()
            assert not _

            self.emit(f'result.append(substitute_variables({value!r}, namespace))')
            self.match(self.lookahead.type)
            self.parse_text()
        elif self.lookahead.type in self.First['control']:
            self.parse_control()
            self.parse_text()
        elif self.lookahead.type in self.Follow['text']:
            self.emit('...')
        else:
            self.error(c_code | self.First['control'] | self.Follow['text'])
        '''

        while True:
            if self.lookahead.type in c_code:
                value, *_ = self.lookahead.parse()
                assert len(_) == 0

                self.emit(f'result.append(substitute_variables({value!r}, namespace))')
                self.match(self.lookahead.type)
            elif self.lookahead.type in self.First['control']:
                self.parse_control()
            elif self.lookahead.type in self.Follow['text']:
                self.emit('...')
                return
            else:
                self.error(c_code | self.First['control'] | self.Follow['text'])

    def parse(self):
        self.write_header()

        self.parse_text()

        if not self.EOF:
            # sometimes we don't hit EOF, tha's probably fine
            self.match(self.lookahead.type)

            # but if the next character is not EOF either, there's a problem
            if not self.EOF:
                raise RuntimeError('There was an unknown error during parsing: ', self.lookahead)

        return self.code


First = {
    'control': {types.define_simple, types.define_value, types.define_func, types.undef, types.include_globl,
                types.include_local, types.error, types.warning, types.if_, types.ifdef, types.ifndef},
    'conditional': {types.if_, types.ifdef, types.ifndef},
    'if_str': {types.if_, types.ifdef, types.ifndef},
    'elif_blocks': {types.elif_, types.empty},
    'else_block': {types.else_, types.empty},
    'text': {types.define_simple, types.define_value, types.define_func, types.undef, types.include_globl,
             types.include_local, types.error, types.warning, types.if_, types.ifdef, types.ifndef,
             types.c_code, types.empty}
    }

Follow = {
    'elif_blocks': {types.else_, types.endif},
    'else_block': {types.endif},
    'text': {types.elif_, types.else_, types.endif, types.EOF} # need EOF because this is the starting symbol
    }


if __name__ == "__main__":
    import first_pass
    import tokenize
    import time

    code = '''
#ifndef _CDEFS_H_
#define _CDEFS_H_
#if !defined(__sys_cdefs_arch_unknown__) && defined(__i386__)
#elif !defined(__sys_cdefs_arch_unknown__) && defined(__x86_64__)
#else
#error Unsupported architecture
#endif


#endif /* !_CDEFS_H_ */
/*
 * FILE INCLUDED: /Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk/usr/include/Availability.h
 */
/*
 * Copyright (c) 2007-2016 by Apple Inc.. All rights reserved.
 *
 * @APPLE_LICENSE_HEADER_START@
 *
 * This file contains Original Code and/or Modifications of Original Code
 * as defined in and that are subject to the Apple Public Source License
 * Version 2.0 (the 'License'). You may not use this file except in
 * compliance with the License. Please obtain a copy of the License at
 * http://www.opensource.apple.com/apsl/ and read it before using this
 * file.
 *
 * The Original Code and all software distributed under the License are
 * distributed on an 'AS IS' basis, WITHOUT WARRANTY OF ANY KIND, EITHER
 * EXPRESS OR IMPLIED, AND APPLE HEREBY DISCLAIMS ALL SUCH WARRANTIES,
 * INCLUDING WITHOUT LIMITATION, ANY WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE, QUIET ENJOYMENT OR NON-INFRINGEMENT.
 * Please see the License for the specific language governing rights and
 * limitations under the License.
 *
 * @APPLE_LICENSE_HEADER_END@
 */

#ifndef __AVAILABILITY__
#define __AVAILABILITY__
#define HEY
#endif
    '''

    fname = 'file.c'

    print("First pass...")
    s = time.process_time()
    code = first_pass.first_pass(code)
    e = time.process_time()
    print(f"First pass done in {e-s} seconds")

    print("Tokenizing...")
    s = time.process_time()
    tokens = list(tokenize.tokenize(code, types))
    #print(tokens)
    e = time.process_time()
    print(f"Tokenized in {e - s} seconds")

    print("Parsing...")
    s = time.process_time()
    ret = Parser(fname, tokens, First, Follow).parse()
    e = time.process_time()
    print(f"Parsed in {e - s} seconds")

    python_code = '\n'.join(map(str, ret))

    #print(python_code, '\n\n')

    # execute this
    substitute_variables = lambda string, namespace: string

    def include(fname: str, paths: list, GLOBALS: dict) -> None:
        import os.path

        for path in paths:
            full_path = os.path.join(path, fname)

            try:
                with open(full_path) as f:
                    print(f'Including file {full_path!r}')
                    header_code = first_pass.first_pass(f.read())
                    tokens = tokenize.tokenize(header_code, types)

                    ret = Parser(tokens, First, Follow).parse()

                    python_code = '\n'.join(map(str, ret))

                    exec(python_code, GLOBALS, {})
                    #print(f'Included file {full_path!r}')
                    #print(GLOBALS['namespace'])

                    return
            except:
                ...

        raise FileNotFoundError(f'Include file {fname!r} was not found')

    namespace, result = {'__i386__': True}, []
    paths_global = [
        '/usr/local/include',
        '/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib/clang/9.1.0/include',
        '/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/include',
        '/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk/usr/include'
        ]
    paths_local = []

    GLOBALS = {
        '__builtin__': {'print': print},
        'namespace': namespace,
        'result': result,
        'paths_global': paths_global,
        'paths_local': paths_local,
        'substitute_variables': substitute_variables,
        'include': include
        }

    #print(python_code)

    exec(python_code, GLOBALS, {})

    print('\n'.join(result))

    print("\nNamespace:", namespace)