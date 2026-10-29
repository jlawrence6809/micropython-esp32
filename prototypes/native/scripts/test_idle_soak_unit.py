#!/usr/bin/env python3
"""Offline single-attempt/sanitization/invariant/report tests; no device I/O."""
import json
from pathlib import Path
import tempfile
import unittest
import urllib.error
from unittest import mock
import test_idle_soak as soak


class SoakTests(unittest.TestCase):
    def setUp(self):
        self.initial = dict(boot_id='boot', elf_sha256='image', revision='edit')

    def test_radio_report_excludes_network_identity(self):
        data = dict(sta_ssid='private', sta_ip='192.0.2.1', password='private', sta_rssi=-53,
                    sta_connected=True, disconnect_count=0, last_disconnect_reason=0)
        result = soak.metrics('/api/wifi/status', data)
        self.assertNotIn('private', json.dumps(result))
        self.assertNotIn('192.0.2.1', json.dumps(result))
        self.assertEqual(result['sta_rssi'], -53)
        self.assertEqual(soak.metrics('/api/profile/edit', {'profile': {'secret': True}}), {})
        self.assertEqual(soak.metrics('/api/wifi/status', {'sta_rssi':{'password':'private'}}), {})
        watched = soak.metrics('/api/watchdog/status', {'observed_progress_age_ms':{'rules':10,'network':'private','ssid':'private'}})
        self.assertEqual(watched, {'observed_progress_age_ms':{'rules':10}})

    def test_status_rows_are_allowlisted(self):
        result = soak.metrics('/api/status', [{'key':'free_heap', 'value':1234}, {'key':'unknown', 'value':'private'}])
        self.assertEqual(result, {'free_heap':1234})

    def test_timeout_and_http_error_never_retried(self):
        for error in (TimeoutError(), urllib.error.HTTPError('unused', 503, 'no', None, None)):
            b = mock.Mock(); b.get.side_effect = error
            result = soak.sample(b, '/api/status', self.initial, 0)
            self.assertFalse(result['ok'])
            self.assertEqual(b.get.call_count, 1)
            b.upload.assert_not_called()

    def test_boot_and_explicit_edit_changes_flagged(self):
        result = soak.check_identity('/api/profile/edit', dict(boot_id='other', revision='new'), self.initial)
        self.assertIn('edit_boot_changed', result)
        self.assertIn('explicit_configuration_changed', result)
        self.assertEqual(soak.check_identity('/api/profile/edit', dict(self.initial, profile={'value':True}), self.initial), [])
        self.assertTrue(soak.check_identity('/api/engine/status', {'backend':'gpio'}, self.initial))
        self.assertTrue(soak.check_identity('/api/watchdog/status', {'monitor_active':True, 'timeout_mask':1}, self.initial))

    def test_summary_heap_loss_and_no_missing_metrics_success(self):
        values = [dict(ok=True, latency_s=.1, metrics={'free_heap':190000, 'sta_rssi':-53, 'disconnect_count':1}),
                  dict(ok=False, latency_s=4, metrics={'free_heap':150000, 'sta_rssi':-54, 'disconnect_count':2})]
        result = soak.summarize(values)
        self.assertEqual(result['failed'], 1)
        self.assertEqual(result['disconnect_delta'], 1)
        self.assertEqual(result['heap']['retained_delta'], -40000)
        self.assertFalse(result['heap_headroom_ok'])
        self.assertFalse(soak.summarize([dict(ok=True, latency_s=.1)])['heap_headroom_ok'])

    def test_reports_private_mode_no_overwrite_or_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'report.json'
            soak.write_report(path, {'ok':True})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                soak.write_report(path, {'ok':False})
            link = Path(directory)/'link.json'; link.symlink_to(path)
            with self.assertRaises(OSError):
                soak.write_report(link, {'ok':False})
            self.assertEqual(json.loads(path.read_text()), {'ok':True})


if __name__ == '__main__':
    unittest.main()
