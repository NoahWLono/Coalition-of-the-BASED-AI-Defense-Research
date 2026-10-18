"""Synthetic regression checks for publication redaction; no host identifiers."""
import importlib.util
from pathlib import Path
import struct
import hashlib
import json
import tempfile
import unittest

from pymavlink.dialects.v20 import ardupilotmega as mav

SCRIPT = Path(__file__).with_name('sanitize_publication.py')
OLD = b'abcdefabcdefabcdefabcdefabcdefab'
NEW = b'00000000000000000000000000000011'


class PublicationRedactionTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.is_file(), 'The publication redactor must exist')
        spec = importlib.util.spec_from_file_location('publication_redactor', SCRIPT)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def record(self, message, version1=False):
        packet = message.pack(mav.MAVLink(None), force_mavlink1=version1)
        return struct.pack('>Q', 1700000000123456) + packet

    def test_v1_v2_text_redaction_preserves_timestamp_and_valid_crc(self):
        for version1 in (True, False):
            source = self.record(mav.MAVLink_statustext_message(6, b'SITL ' + OLD), version1)
            result, report = self.module.sanitize_tlog(source, OLD, NEW)
            self.assertNotIn(OLD, result)
            self.assertIn(NEW, result)
            self.assertEqual(source[:8], result[:8])
            self.assertEqual(len(source), len(result))
            self.assertEqual(report['changed_messages'], 1)
            parsed = mav.MAVLink(None).parse_char(result[8:])
            self.assertEqual(parsed.text, 'SITL ' + NEW.decode())

    def test_uid2_prefix_is_redacted_without_changing_commit_or_flight_values(self):
        commit = list(b'7ce11b41')
        msg = mav.MAVLink_autopilot_version_message(5, 123, 0, 0, 7, commit, [0]*8, [0]*8, 1, 2, 0, list(OLD[:18]))
        source = self.record(msg)
        result, report = self.module.sanitize_tlog(source, OLD, NEW)
        parsed = mav.MAVLink(None).parse_char(result[8:])
        self.assertEqual(bytes(parsed.uid2), NEW[:18])
        self.assertEqual(parsed.flight_custom_version, commit)
        self.assertEqual(parsed.flight_sw_version, 123)
        self.assertEqual(report['changed_fields'], {'AUTOPILOT_VERSION.uid2': 1})

    def test_actual_sitl_uid2_preserves_terminating_nul(self):
        msg = mav.MAVLink_autopilot_version_message(5, 123, 0, 0, 7, list(b'7ce11b41'), [0]*8, [0]*8, 1, 2, 0, list(OLD[:17]+b'\0'))
        source = self.record(msg)
        result, _ = self.module.sanitize_tlog(source, OLD, NEW)
        parsed = mav.MAVLink(None).parse_char(result[8:])
        self.assertEqual(bytes(parsed.uid2), NEW[:17]+b'\0')
        self.assertEqual(len(source), len(result))

    def test_invalid_crc_and_truncated_record_are_rejected(self):
        source = self.record(mav.MAVLink_statustext_message(6, b'SITL ' + OLD))
        for damaged in (source[:-1], source[:-1] + bytes([source[-1] ^ 1])):
            with self.assertRaises(ValueError):
                self.module.sanitize_tlog(damaged, OLD, NEW)

    def test_unrelated_telemetry_is_byte_identical(self):
        source = self.record(mav.MAVLink_heartbeat_message(2, 3, 81, 9, 4, 3))
        result, report = self.module.sanitize_tlog(source, OLD, NEW)
        self.assertEqual(source, result)
        self.assertEqual(report['changed_messages'], 0)

    def test_matching_nan_sensor_fields_compare_equal_but_numeric_changes_do_not(self):
        compare = getattr(self.module, 'equivalent_fields', None)
        self.assertIsNotNone(compare, 'Decoded comparisons must account for matching NaN sensor fields')
        self.assertTrue(compare({'value': float('nan'), 'height': 12.0}, {'value': float('nan'), 'height': 12.0}))
        self.assertFalse(compare({'value': float('nan'), 'height': 12.0}, {'value': float('nan'), 'height': 13.0}))

    def test_aggregate_input_hash_references_converge_without_editing_originals(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)/'source'; destination = Path(temporary)/'destination'
            for root in (source, destination):
                (root/'evidence').mkdir(parents=True)
            original = b'original private input'; derivative = b'public derivative input'
            (source/'evidence/input.txt').write_bytes(original)
            (destination/'evidence/input.txt').write_bytes(derivative)
            first = json.dumps({'input_sha256': hashlib.sha256(original).hexdigest()}).encode()
            second = json.dumps({'report_sha256': hashlib.sha256(first).hexdigest()}).encode()
            for root in (source, destination):
                (root/'evidence/first.json').write_bytes(first)
                (root/'evidence/captured-stdout.txt').write_bytes(first)
                (root/'evidence/second.json').write_bytes(second)
            (destination/'evidence/first.json').write_text(json.dumps({'input_sha256': hashlib.sha256(derivative).hexdigest()}))
            report = self.module.refresh_aggregate_references(source, destination, {'changed_files': []})
            updated_first = (destination/'evidence/first.json').read_bytes()
            self.assertEqual(json.loads(updated_first)['input_sha256'], hashlib.sha256(derivative).hexdigest())
            self.assertEqual(json.loads((destination/'evidence/second.json').read_bytes())['report_sha256'], hashlib.sha256(updated_first).hexdigest())
            self.assertEqual((source/'evidence/first.json').read_bytes(), first)
            self.assertEqual((source/'evidence/second.json').read_bytes(), second)
            self.assertEqual((destination/'evidence/captured-stdout.txt').read_bytes(), updated_first)
            self.assertEqual(len(report['aggregate_reference_refresh']['files']), 2)


if __name__ == '__main__':
    unittest.main()
