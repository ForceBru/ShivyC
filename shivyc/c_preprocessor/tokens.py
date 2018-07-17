import re
import enum

"""
This file contains all the token types the parser for the preprocessor language recognizes.
They're split into two parts:
    'Preproc.Tok_types' contains the instruction tokens (like 'define', 'include', etc)
    'Expr.Tok_types' contains tokens necessary to pythonize expressions and tokenize C code to do substitution later on
    
"Pythonizing expressions" means making expressions after '#if' and '#elif' executable by the Python interpreter. This includes
removing the 'L' or 'U' suffixes after an integer, retrieving names defined by '#define' and converting some operators
(like '||' and '&&') into their Python synonyms.
"""


class Token:
    def __init__(self, type, matchobj, lineno: int):
        self.type, self.matchobj, self.lineno = type, matchobj, lineno
        self.value = self.matchobj[0].rstrip()

    def __str__(self):
        return f'{self.type}({self.value!r}, line {self.lineno})'

    __repr__ = __str__


s, s_ = r'[ \t]', r'[ \t]*'  # space
n, n_ = r'[\r\n]', r'[^\r\n]' # newline
id = r'[a-zA-Z_][a-zA-Z_0-9]*'
file_name = r'[a-zA-Z_0-9./-]+'
control = lambda name: fr'{s_}#{s_}{name}{s}'

# these are the regular expressions used to extract various tokens by 'c_preprocessor.tokenize.tokenize'
preproc_tok_regexes = {
    'define_simple': fr'(?P<define_simple>{s_}#{s_}define{s}+(?P<name>[a-zA-Z_]\w*){s_}(?:\n|\Z))',
    'define_func'  : fr'(?P<define_func>{s_}#{s_}define{s}+(?P<name>[a-zA-Z_]\w*)\({s_}(?P<args>(?:(?:\.\.\.)|[a-zA-Z_]\w*)(?:(?<!\.\.\.)(?:{s_},{s_}(?:(?:\.\.\.)|[a-zA-Z_]\w*)))*)?{s_}\)(?:{s_}|(?:{s}+(?P<value>[^\n]+)))(?:\n|\Z))',
    'define_value' : fr'(?P<define_value>{s_}#{s_}define[ \t]+(?P<name>[a-zA-Z_]\w*){s}+(?P<value>[^\n]+)(?:\n|\Z))',
    'undef'        : fr'{control("undef")}+({id}){n}',

    'include_globl': fr'{control("include")}+<{s_}({file_name}){s_}>{s_}{n}',
    'include_local': fr'{control("include")}+"{s_}({file_name}){s_}"{s_}{n}',

    'line_name'    : fr'{control("line")}+(.+){s}"({file_name})"{s_}{n}',
    'line_simple'  : fr'{control("line")}+({n_}+){n}',

    'error'        : fr'{control("error")}+({n_}*){n}',
    'warning'      : fr'{control("warning")}+({n_}+){n}',

    'ifdef'        : fr'{control("ifdef")}+({id}){s_}{n}',
    'ifndef'       : fr'{control("ifndef")}+({id}){s_}{n}',
    'if_'          : fr'{control("if")}+({n_}+){n}',
    'elif_'        : fr'{control("elif")}+({n_}+){n}',
    'else_'        : fr'{control("else")}*{n}',
    'endif'        : fr'{control("endif")}*{n}',

    'empty'        : fr'{control("")}*$',
    'EOF'          : fr'{control("")}*$',

    'c_code'       : r'([^#][^\n]*)(?:\n|\Z)'  # do not allow hashes at the beginning of a line
    }

expr_tok_regexes = {
    'string': r'"[^"]*"',
    'character': r"'\w'",

    'defined': fr'defined{s_}\({s_}({id}){s_}\)',

    'id': id,
    'int_hex': r'(\+|-)?(0[xX][0-9a-fA-F]+)[LlUu]?',
    'int': r'(\+|-)?(0|[1-9][0-9]*)[LlUu]?',
    'float': r'(\+|-)?(0|[1-9][0-9]*)?\.[0-9]+',

    'lpar': r'\(',
    'rpar': r'\)',
    'lbrace': '{',
    'rbrace': '}',
    'lbrack': r'\[',
    'rbrack': r'\]',

    'threedots': r'\.\.\.',

    'plusplus': r'\+\+',
    'minusminus': r'--',
    'plus': r'\+',
    'minus': '-',
    'star': r'\*',
    'slash': '/',

    'squote': "'",
    'dquote': '"',

    'le': '<=',
    'ge': '>=',
    'lt': '<',
    'gt': '>',
    'eq': '==',
    'ne': '!=',

    'assign': '=',

    'or_': r'\|\|',
    'and_': r'&&',

    'not_': '!',
    'question': r'\?',
    'comma': ',',
    'semicolon': ';',
    'colon': ':',

    'other': '(.)'
    }


# these are all the token types the lexer recognizes
class Preproc:
    Tok_types = enum.Enum('Tok_types_p', {key: re.compile(value) for key, value in preproc_tok_regexes.items()})

class Expr:
    Tok_types = enum.Enum('Tok_types_e', {key: re.compile(value) for key, value in expr_tok_regexes.items()})