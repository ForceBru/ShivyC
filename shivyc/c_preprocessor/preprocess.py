import os.path
import os

from . import first_pass
from . import tokens
from . import tokenize
from . import parse

from . import caching

"""
This does the actual preprocessing:

    * Transpiles the preprocessor directives of the program to Python
    * Executes the resulting Python code
        * This code does the actual macro definition, conditional compilation and file inclusion
        * It also attempts to do macro substitution for each 'c_code' token
    * Outputs the resulting C code without any preprocessor directives
    
WARNING: when a file is included for the first time, it must undergo the process described above. Depending on its
    size and complexity, it may take some time to process it. However, all the files except the one that initiated the process
    are cached, so that including them later will be lightning-fast.
"""


CACHE = caching.Cache('cache')


def preprocessor_to_python(code: str, file_path: str, cache=True):
    """

    :param code: the code to translate to Python
    :param file_path: the path to the file to be translated
    :param cache: whether o cache the result or not (should be True for included files)
    :return:
    """
    if cache:
        try:
            compiled = CACHE[file_path]
            return compiled
        except KeyError:
            ...

    code = first_pass.first_pass(code)
    Tokens = tokenize.tokenize(code, tokens.Preproc.Tok_types)

    ret = parse.Parser(file_path, Tokens, parse.First, parse.Follow).parse()

    python_code = '\n'.join(map(str, ret))

    if cache:
        print(f'\tCaching file {file_path!r}...')
        compiled = CACHE.cache(file_path, python_code)
        print(f'\tFile {file_path!r} cached successfully!')
    else:
        compiled = compile(python_code, file_path, 'exec', optimize=2)

    return compiled


def get_value_by_name(name: str, namespace: dict):
    if not name in namespace:
        return 0

    result = namespace[name]

    try:
        while namespace[result]:
            result = namespace[result]
    except KeyError:
        ...

    try:
        return eval(result)
    except:
        ...

    return result


def include(fname: str, paths: list, GLOBALS: dict, current_file_path: str, local=False) -> None:
    assert isinstance(fname, str)

    if not paths:
        raise FileNotFoundError(f'File {fname!r} was not included, because no search paths were supplied')

    current_path = os.path.split(current_file_path)[0]
    parent_path = os.path.split(current_path)[0]

    for path in paths + ([current_path, parent_path] if local else []):
        full_path = os.path.join(path, fname)

        try:
            with open(full_path, encoding='utf8') as f:
                print(f"Including file {full_path!r}...")
                header_data = f.read()

                python_code = preprocessor_to_python(header_data, full_path)

                exec(python_code, GLOBALS, {}) # this modifies GLOBALS in-place

                print(f'Included file {full_path!r}')

                return
        except FileNotFoundError as e:
            err_msg = e

    raise FileNotFoundError(f'File {fname!r} was not included, because:\n{err_msg}')


def substitute_variables(code: str, namespace: dict):
    Tokens = list(tokenize.tokenize(code, tokens.Expr.Tok_types))

    for i, tok in enumerate(Tokens):
        if tok.type != tokens.Expr.Tok_types.id:
            continue

        try:
            assert isinstance(tok.value, str)

            if tok.value in namespace:
                value = get_value_by_name(tok.value, namespace)
            else:
                raise KeyError()
        except KeyError:
            continue

        if not getattr(value, '__call__', None):  # this is not a function-like macro
            tok.value = str(value)
            continue

        # THIS IS A FUNCTION-LIKE MACRO, buckle up, let's get hacking!

        # Idea: get the longest streak of matching parentheses and replace it with the needed substitution
        j = i + 1

        if Tokens[j].type == tokens.Expr.Tok_types.lpar:
            open_parens, closing_parens = 1, 0
            j += 1
        else:
            raise SyntaxError(f'Expected a function-like macro call, got {tokens[j]}')

        arg_indices = [j]  # indices of individual arguments

        try:
            while open_parens != closing_parens:
                # commas separate streaks of matching parentheses while the first opening parenthesis remains unmatched
                if open_parens - closing_parens == 1 and Tokens[j].type == tokens.Expr.Tok_types.comma:
                    arg_indices.append(j)

                if Tokens[j].type == tokens.Expr.Tok_types.lpar:
                    open_parens += 1
                elif Tokens[j].type == tokens.Expr.Tok_types.rpar:
                    closing_parens += 1

                j += 1
        except IndexError:
            raise SyntaxError(f'Unmatched parentheses found ({open_parens, closing_parens} at tokens {i, j} out of {len(Tokens)}) in {code!r}')

        arg_indices.append(j - 1)

        # retrieve the arguments' tokens
        # this looks ugly but works
        args = (Tokens[arg_indices[i] + (i != 0):arg_indices[j]] for i, j in
                zip(range(len(arg_indices)), range(1, len(arg_indices))))

        args_strings = [' '.join(tok.value for tok in arg) for arg in args]

        if '' in args_strings:
            raise SyntaxError(f'Function-like macro call must not contain empty arguments (got {args_strings})')

        if args_strings == ['void']: # apparently, this is a declaration...
            # do nothing
            continue

        try:
            # do the substitution
            sub = value(*args_strings)

            Tokens[i].value = substitute_variables(sub, namespace)
        except TypeError as e:
            raise SyntaxError(f'Function-like macro does not take {len(args_strings)} arguments:', e)

        # eliminate that streak of matching parentheses
        for t in range(i + 1, j):
            Tokens[t].value = ''

    return ' '.join(tok.value for tok in Tokens if tok.value)


def preprocess(code: str, file_name: str, cache=False, paths_global=[], paths_local=['.'], namespace={}):
    python_code = preprocessor_to_python(code, file_name, cache)

    result = []

    GLOBALS = {
        '__builtin__'         : {'print': print},
        'namespace'           : namespace,
        'result'              : result,
        'paths_global'        : paths_global,
        'paths_local'         : paths_local,
        'substitute_variables': substitute_variables,
        'include'             : include,
        'get_value_by_name'   : get_value_by_name
        }

    # this does the substitution and conditional compilation and writes the appropriate lines of C code into a list called 'result'
    exec(python_code, GLOBALS, {})

    c_code = '\n'.join(result)

    return namespace, c_code


if __name__ == '__main__':
    code = r'''
#include <stdarg.h>
#define T 5
#define FUN(x, y) ((x) + (y))

int main() {
    printf("Hello, world!\n");
    return FUN(T, 7 + FUN(T, 2));
}
    '''

    paths_global = [
        '/usr/local/include',
        '/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib/clang/9.1.0/include',
        '/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/include',
        '/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk/usr/include'
        ]
    namespace = {'__i386__': True, 'DEBUG': True}


    namespace, c_code = preprocess(code, 'file.c', paths_global=paths_global, namespace=namespace)

    print(c_code)