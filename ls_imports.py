import ast
import glob
import imp
import json
import os

import networkx as nx
from networkx.readwrite import json_graph


def camel_case(s):
    """Check whether string is camel case."""
    return (s != s.lower() and s != s.upper())


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
            name = node.level * '.'
            if node.module:
                name += node.module
                if not camel_case(alias.name):
                    name += '.' + alias.name
                # else:
                    # print("Found CamelCased Alias: %s" % alias.name)
            else:
                name += alias.name
            self._modules.append((node.lineno + self._lineno, name))

    def visit(self, node):
        """Visit a node but not recursively."""
        for node in ast.walk(node):
            method = 'visit_' + node.__class__.__name__
            getattr(self, method, lambda x: x)(node)

    @property
    def modules(self):
        return self._modules


def dirname(path):
    return os.path.split(path)[0]


def module_path_to_name(path, project_root):
    """
    Convert a file path to a canonical module name.

    /root/path/to/module.py -> path.to.module
    """
    return path.replace(project_root, '').replace('.py', '').replace('/', '.')


def get_imported_modules(src_path, project_root):
    """Get all modules imported by a single python file."""
    with open(src_path, 'rb') as inp:
        code = inp.read()

    try:
        ic = ImportChecker()
        parsed = ast.parse(code)
        ic.visit(parsed)
    # Ignore SyntaxError in Python code.
    except SyntaxError:
        return []

    # Get all imported modules
    modules = [m[1] for m in ic.modules]

    # Get module paths
    modules = {
        module_name: find_module_path(module_name, project_root, src_path)
        for module_name in modules
    }

    # Convert all module names to canonical form
    modules = [
        module_path_to_name(v, project_root)
        if v else k for k, v in modules.items()
    ]

    return set(modules)


# TODO: Better names for these functions
def find_module_path(module_name, project_root, src_path):
    """Find the file that will be imported from module_name."""

    def find_dotted(name, path=None):
        for x in name.split('.'):
            if path is not None:
                path = [path]
            try:
                _, path, _ = imp.find_module(x, path)
            except ImportError:
                return ''
        return path

    p = find_dotted(module_name, project_root)

    if not p:
        # Move up the directory structure for as many dots as in module_name
        root = src_path
        while module_name.startswith('.'):
            module_name = module_name[1:]
            root = dirname(root)

        p = find_dotted(module_name, root)

    return p

if __name__ == '__main__':
    import sys

    src_path = sys.argv[1]
    project_root = '/home/dufferzafar/dev/mitmproxy/'

    if os.path.isdir(src_path):
        files = glob.glob(src_path + '*.py') + glob.glob(src_path + '**/*.py')
    else:
        files = [src_path]

    modules = {}
    for file in files:
        modules[module_path_to_name(file, project_root)] = [
            m for m in get_imported_modules(file, project_root)
            if m.startswith(module_path_to_name(src_path, project_root))
        ]

    G = nx.DiGraph()
    for trgt in modules:
        G.add_node(trgt)
        for src in modules[trgt]:
            G.add_edge(src, trgt)

    with open('html/graph.json', 'w') as out:
        json.dump(json_graph.node_link_data(G), out, indent=4)
