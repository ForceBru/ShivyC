import os
import os.path

import marshal

class Cache:
    """
    This class is responsible for caching the results of translating the preprocessor code to Python.
    """
    def __init__(self, cache_path: str):
        self.path = cache_path

    def __prepare_path(self, path):
        if os.path.isabs(path):
            cache_path = self.path + path
        else:
            cache_path = os.path.join(self.path, path)

        return os.path.normpath(cache_path)

    def cache(self, file_path, python_code, force=False):
        assert isinstance(file_path, str)

        cache_path = self.__prepare_path(file_path + '.py')

        path, file_name = os.path.split(cache_path)

        try:
            os.makedirs(path)
        except OSError:
            ...

        with open(cache_path, 'w') as f:
            f.write(python_code)

        if force or not os.path.exists(cache_path + 'c'):
            with open(cache_path + 'c', 'wb') as f:
                compiled = compile(python_code, file_path, 'exec', optimize=2)
                marshal.dump(compiled, f)
        else:
            compiled = self[file_path]

        return compiled

    def __getitem__(self, file_path):
        assert isinstance(file_path, str)

        cache_path = self.__prepare_path(file_path + '.pyc')

        if not os.path.exists(cache_path):
            raise KeyError(f'Could not find file {file_path!r} in the cache')

        with open(cache_path, 'rb') as f:
            try:
                return marshal.load(f)
            except (EOFError, ValueError, TypeError) as e:
                raise KeyError(f'File {file_path!r} was found, but failed to load because: {e}')


if __name__ == '__main__':
    code = r'''
print("Hello world!")

if namespace['wow']:
    raise
else:
    print('amazing!')
    '''

    cache = Cache('cache')

    cache.cache('test.h', code, True)

    exec(cache['test.h'], {'namespace': {'wow': 0}})