"""Exercise the documented direct-script CLI without inherited import paths."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class PrefixCliTests(unittest.TestCase):
    def test_direct_cli_loads_prefix_adapter_before_directory_validation(self):
        env = dict(os.environ)
        env.pop('PYTHONPATH', None)
        with tempfile.TemporaryDirectory(prefix='bukhari-cli-') as temp:
            absent = Path(temp) / 'not-created'
            result = subprocess.run(
                [sys.executable, '-I', str(ROOT / 'scripts/release_distribution.py'),
                 'validate', '--config', 'release/distribution-prefix-v1.config.json',
                 '--directory', str(absent)],
                cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 1)
        self.assertIn('missing/extra distribution artifact', result.stderr)
        self.assertNotIn('Traceback', result.stderr)

if __name__ == '__main__':
    unittest.main()
