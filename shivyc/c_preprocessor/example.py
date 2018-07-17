import sys
sys.path.insert(0, '..')

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

paths_global = [
        '/usr/local/include',
        '/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib/clang/9.1.0/include',
        '/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/include',
        '/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk/usr/include'
        ]
namespace = {'__i386__': True, 'DEBUG': True}

namespace, preprocessed = preprocess(
    code,
    'file.c',
    paths_global=paths_global,
    namespace=namespace
)

print(preprocessed)