## `c_preprocessor` - a C preprocessor written from scratch in pure Python without any external dependencies

This module provides an immplementation of the C preprocessor.

#### Features supported
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
* Recognition and processing of non-preprocessor directives:

      int main(void) {
          puts("hello, world!");
          return 0;
      }

#### TODO:
* Concatenation:

      VAR1 ## VAR2
* Stringification:

      #VAR
* Variable number of arguments in macros:

      #define FOO(...)       printf(__VA_ARGS__)

### How to use
This module has only one function that's useful to the user:

    c_preprocessor.preprocess.preprocess(code: str, file_name: str, cache=False, paths_global=[], paths_local=['.'], namespace={})

The main arguments are the following:
* `code` - the string that needs to be preprocessed;
* `file_name` - the name of the file where `code` has been read from;
* `cache` - whether to cache the results of processing this particular file;
* `paths_global` - the list of paths (strings) where to search for global includes (in the form `#include <file>`);
* `paths_local` - the list of paths (strings) where to search for local includes (in the form `#include "file"`);
* `namespace` - the dictionary of macros that should be defined prior to any processing;

### Example:

    from c_preprocessor import preprocess

    code = r'''
    #include <stdio.h>

    int main(void) {
    #ifdef DEBUG
    puts("This is a debug build!");
    #else
    puts("This is a release build.");
    #endif

    puts("WELCOME TO MY AWESOME PROGRAM!");

    return 0;
    }
    '''

    namespace, preprocessed = preprocess(
        code,
        'file.c',
        paths_global=['/usr/local/include'],
        namespace={'DEBUG': True}
    )

The output may be pretty huge, so refer to `c_preprocessor/example.py` for an example. Make sure to use the correct include paths.