import re
import os


def splice(string: str) -> str:
    """
    Remove all <backslash> + <newline> combinations.
    :param string: input code
    """
    return string.replace('\\\n', ' ')


def delete_comments(string):
    comment_multiline = re.compile(r'/\*+[^*]*\*+(?:[^/*][^*]*\*+)*/')
    comment_oneline = re.compile(r'//.*')
    c_string = re.compile(r'"[^"]*"')

    i, end = 0, len(string)
    while i < end:
        # this is way faster than using regexes right away
        if string[i] not in '"/':  # adding this line increases speed by 22%
            ...
        elif string[i] == '"':
            m = c_string.match(string[i:])

            if m:  # no comments inside strings
                _, _i = m.span()

                yield string[i:i + _i]
                i += _i
                continue
        elif string[i] == '/':
            m = comment_multiline.match(string[i:]) or comment_oneline.match(string[i:])

            if m:
                i += m.span()[-1]

                yield from '\n' * m[0].count('\n')

                continue

        yield string[i]
        i += 1


def first_pass(string):
    return ''.join(delete_comments(splice(string)))


if __name__ == "__main__":
    code = r'''
/* this is a comment
 * a multiline comment
 */
 # define f(x, y) sin(x) / \
pi + 5 * cos(x)
#include <stdio.h> //this includes some stuff
int main(void) {
    puts("this /*must not*/ be removed");
    int p = /*0*/1;
    return p;//0;
}
#undef f

#if __has_extension(attribute_deprecated_with_message) || \
		(defined(__GNUC__) && ((__GNUC__ >= 5) || ((__GNUC__ == 4) && (__GNUC_MINOR__ >= 5))))
	#define __deprecated_msg(_msg) __attribute__((deprecated(_msg)))
#else
	#define __deprecated_msg(_msg) __attribute__((deprecated))
#endif
#ifdef __SWIFT_COMPILER_VERSION
    #define __swift_compiler_version_at_least_impl(X, Y, Z, a, b, ...) \
    __SWIFT_COMPILER_VERSION >= ((X * UINT64_C(1000) * 1000 * 1000) + (Z * 1000 * 1000) + (a * 1000) + b)
    #define __swift_compiler_version_at_least(...) __swift_compiler_version_at_least_impl(__VA_ARGS__, 0, 0, 0, 0)
#else
    #define __swift_compiler_version_at_least(...) 1
#endif
    '''

    import timeit

    sec = timeit.repeat('first_pass(code)', globals=globals(), number=2, repeat=5)

    print(max(sec), sec) # 2.8157414380002592