"""TEL-41: the backend writes through loggers, never through `print` (a `print` skips the redaction and the JSON format)."""
import ast
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

SKIPPED_DIRECTORIES = {'.venv', 'venv', 'migrations', '__pycache__', 'node_modules', 'staticfiles'}
# Test files, and the helper whose job is to run a child interpreter whose own `print` is the channel of its report.
EXEMPT_FILES = {'process_testing.py', 'tests.py'}


def production_files(root):
    for path in sorted(Path(root).rglob('*.py')):
        relative = path.relative_to(root)
        if SKIPPED_DIRECTORIES & set(relative.parts):
            continue
        name = path.name
        if name in EXEMPT_FILES or name.startswith('test_') or name.endswith('_test.py') or 'tests' in relative.parts:
            continue
        if name == 'manage.py':
            continue
        yield path


def print_calls(source):
    return [
        node.lineno for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'print'
    ]


class NoPrintTests(SimpleTestCase):
    def test_no_module_of_the_backend_calls_print(self):
        offenders = {}
        scanned = 0
        for path in production_files(settings.BASE_DIR):
            scanned += 1
            lines = print_calls(path.read_text(encoding='utf-8'))
            if lines:
                offenders[str(path.relative_to(settings.BASE_DIR))] = lines
        self.assertGreater(scanned, 50, 'the scan must reach the apps, or it proves nothing')
        self.assertEqual(offenders, {})

    def test_the_scan_sees_a_print_and_ignores_other_names(self):
        self.assertEqual(print_calls('x = 1\nprint(x)\nif x:\n    print("a")\n'), [2, 4])
        self.assertEqual(print_calls('logger.print(1)\npprint(1)\nprinter(1)\n'), [])
