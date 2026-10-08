"""Verify locked downloads resume safely without GitHub API discovery."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import setup_assets
import download
import urllib.error


class AssetSetupTests(unittest.TestCase):
    def test_locked_partial_cache_and_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dest = root / 'panda'
            dest.mkdir()
            (dest / 'cached.xml').write_bytes(b'cached')
            lock = root / 'lock.json'
            lock.write_text(json.dumps({'commit': 'pinned', 'sha256': {
                'cached.xml': hashlib.sha256(b'cached').hexdigest(),
                'missing.xml': hashlib.sha256(b'missing').hexdigest()}}))
            with patch.object(setup_assets, 'DEST', dest), patch.object(setup_assets, 'LOCK', lock):
                with patch.object(setup_assets, 'fetch', return_value=b'corrupted') as fetch:
                    with self.assertRaisesRegex(RuntimeError, 'checksum'):
                        setup_assets.main()
                    self.assertEqual(fetch.call_count, 1)
                    self.assertNotIn('api.github.com', fetch.call_args.args[0])
                    self.assertFalse((dest / 'missing.xml').exists())
                with patch.object(setup_assets, 'fetch', return_value=b'missing') as fetch:
                    setup_assets.main()
                    self.assertEqual(fetch.call_count, 1)
                    self.assertTrue((dest / 'manifest.json').exists())
                with patch.object(setup_assets, 'fetch') as fetch:
                    setup_assets.main()
                    fetch.assert_not_called()

    def test_retry_is_bounded_and_permanent_errors_fail_fast(self):
        with patch.object(download.urllib.request, 'urlopen', side_effect=urllib.error.URLError('offline')) as open_url, patch.object(download.time, 'sleep'):
            with self.assertRaises(urllib.error.URLError):
                download.fetch('https://example.com/asset')
            self.assertEqual(open_url.call_count, 4)
        with patch.object(download.urllib.request, 'urlopen', side_effect=urllib.error.HTTPError('url', 404, 'missing', {}, None)) as open_url:
            with self.assertRaises(urllib.error.HTTPError):
                download.fetch('https://example.com/asset')
            self.assertEqual(open_url.call_count, 1)


if __name__ == '__main__':
    unittest.main()
