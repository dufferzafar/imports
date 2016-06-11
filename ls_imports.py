import ast


def file_import_modules(fpath):
    """Get all modules imported by a single python file."""
    with open(fpath, 'rb') as inp:
        code = inp.read()

    try:
        ic = ImportChecker()
        parsed = ast.parse(code)
        ic.visit(parsed)
    # Ignore SyntaxError in Python code.
    except SyntaxError:
        return []

    return ic.modules


class ImportChecker():

    def __init__(self, lineno=1):
        self._lineno = lineno - 1
        self._modules = []

    def visit_Import(self, node):
        """import a [as b]."""
        lineno = node.lineno + self._lineno
        for alias in node.names:
            self._modules.append((lineno, alias.name))

    def visit_ImportFrom(self, node):
        """from a import b [as c]."""
        for alias in node.names:
            name = (node.module or '') + '.' + alias.name
            self._modules.append((node.lineno + self._lineno, name))

    def visit(self, node):
        """Visit a node but not recursively."""
        for node in ast.walk(node):
            method = 'visit_' + node.__class__.__name__
            getattr(self, method, lambda x: x)(node)

    @property
    def modules(self):
        return self._modules


if __name__ == '__main__':
    import sys

    modules = file_import_modules(sys.argv[1])
    modules = [m[1] for m in modules]

    print(modules)
