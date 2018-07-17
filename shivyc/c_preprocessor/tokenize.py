import os

from . import tokens


class PreprocToken(tokens.Token):
    def parse(self) -> 'tuple of str':
        #groups = tuple(v.strip() if v is not None else v for v in self.matchobj.groups())
        groups = self.matchobj.groups()

        if self.type == tokens.Preproc.Tok_types.define_simple:
            return self.matchobj.group('name'),
        elif self.type == tokens.Preproc.Tok_types.define_value:
            return self.matchobj.group('name'), self.matchobj.group('value')
        elif self.type == tokens.Preproc.Tok_types.define_func:
            name, args, value = map(self.matchobj.group, 'name args value'.split())

            if args is None:
                args = ''
            if value is None:
                value = ''

            return name, args, value
        elif self.type in {tokens.Preproc.Tok_types.if_, tokens.Preproc.Tok_types.elif_}:
            assert len(groups) == 1

            return ' '.join(pythonize(groups[0])),

        return groups

class ExprToken(tokens.Token):
    def parse(self) -> str:
        assert isinstance(self.value, str)

        if self.type == tokens.Expr.Tok_types.defined:
            assert len(self.matchobj.groups()) == 1

            ID = self.matchobj[1]

            return f'defined({ID!r})'
        if self.type == tokens.Expr.Tok_types.not_:
            return 'not'
        if self.type == tokens.Expr.Tok_types.or_:
            return 'or'
        if self.type == tokens.Expr.Tok_types.and_:
            return 'and'
        if self.type in {tokens.Expr.Tok_types.int, tokens.Expr.Tok_types.int_hex}:
            ret = self.value.strip()

            while ret[-1] in 'ulUL':
                ret = ret[:-1]

            return ret

        if self.type == tokens.Expr.Tok_types.id:
            assert len(self.matchobj.groups()) == 0

            ID = self.matchobj[0]

            return f'get_value_by_name({ID!r}, namespace)'  # this is connected to parse.Parser

        return self.value


def tokenize(string: str, token_types, ignored={' ', '\t', os.linesep}, token_class=PreprocToken) -> 'generator':
    i, end = 0, len(string)
    lineno = 0

    while i < end:
        while i < end and string[i] in ignored:
            if string[i] == os.linesep:
                lineno += 1

            i += 1

        if i == end:
            return

        for tok_type in token_types:
            m = tok_type.value.match(string, i)

            if not m:
                continue

            yield token_class(tok_type, m, lineno)

            lineno += m[0].count(os.linesep)
            i = m.end()

            break

        if not m:
            raise ValueError(f"Failed to tokenize string starting from line {lineno} ({string[i:].split(os.linesep, 1)[0]})")


def pythonize(string):
    for tok in tokenize(string, tokens.Expr.Tok_types, token_class=ExprToken):
        yield tok.parse()


if __name__ == "__main__":
    import first_pass
    import time

    code = r'''
#ifdef __has_feature
    int p = 1;
    #if __has_feature(attribute_deprecated_with_message)
        #define __AVAILABILITY_INTERNAL_DEPRECATED_MSG(_msg)  __attribute__((deprecated(_msg)))
    #else
        #define __AVAILABILITY_INTERNAL_DEPRECATED_MSG(_msg)  __attribute__((deprecated))
    #endif
#elif defined(__GNUC__) && ((__GNUC__ >= 5) || ((__GNUC__ == 4) && (__GNUC_MINOR__ >= 5)))
    int p = 2;
    #define __AVAILABILITY_INTERNAL_DEPRECATED_MSG(_msg)  __attribute__((deprecated(_msg)))
#else
    int p = 0;
    #define __AVAILABILITY_INTERNAL_DEPRECATED_MSG(_msg)  __attribute__((deprecated))
#endif

int main() {
    puts("hello, world!");
    return 0;
}
    '''
    code = first_pass.first_pass(code)

    with open('../preprocessor_old/failed.c', encoding='utf8') as f:
        code = f.read()

    s0 = time.process_time()
    code = first_pass.first_pass(code)
    e0 = time.process_time()

    print(f'First pass done in {e0 - s0} seconds')

    s1 = time.process_time()
    #result = sum(1 for _ in tokenize(code, tokens.Preproc.Tok_types))
    result = 0
    for tok in tokenize(code, tokens.Preproc.Tok_types):
        print(tok, tok.parse())
        result += 1
    e1 = time.process_time()

    print(f'Tokenized in {e1 - s1} seconds -> {result} tokens')

    #for tok in result:
        #print(tok, tok.parse())