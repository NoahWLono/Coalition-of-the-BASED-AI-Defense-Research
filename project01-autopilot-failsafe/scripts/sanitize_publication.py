#!/usr/bin/env python3
"""Create and verify a public derivative from a separate private evidence tree.

Requires the pinned pymavlink environment. Reads private identifiers locally;
never prints or records their values. Does not run SITL or edit source evidence.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

from pymavlink.dialects.v20 import ardupilotmega as mav
from pymavlink import mavutil

FICTIONAL_MACHINE_ID = b'00000000000000000000000000000011'
FICTIONAL_HOSTNAME = b'failsafe-lab'
FICTIONAL_ROOT = b'/research/project11-autopilot-failsafe'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def equivalent_fields(left, right):
    # DataFlash uses NaN for unavailable measurements; NaN != NaN in Python.
    # The fixed-width byte check and this canonical comparison retain those
    # unavailable values without treating equal NaNs as a sensor change.
    return left == right or json.dumps(left, sort_keys=True) == json.dumps(right, sort_keys=True)


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.chmod(path.stat().st_mode | 0o200)
    path.write_bytes(data)


def sanitize_tlog(data, old_id, new_id):
    """Preserve record bytes except declared identity fields and their CRCs."""
    if len(old_id) != 32 or len(new_id) != 32:
        raise ValueError('Machine identifiers must have exactly 32 bytes')
    decoder = mav.MAVLink(None)
    decoder.robust_parsing = False
    verifier = mav.MAVLink(None)
    verifier.robust_parsing = False
    output = bytearray()
    pos = 0
    counts, fields = Counter(), Counter()
    changed = 0
    while pos < len(data):
        if len(data) - pos < 10:
            raise ValueError('Truncated telemetry record')
        start = pos + 8
        magic, payload_length = data[start:start + 2]
        if magic == 254:
            header_length, packet_length = 6, payload_length + 8
        elif magic == 253:
            if len(data) - start < 12:
                raise ValueError('Truncated MAVLink 2 header')
            if data[start + 2] != 0:
                raise ValueError('Signed or unsupported MAVLink 2 incompatibility flags')
            header_length, packet_length = 10, payload_length + 12
        else:
            raise ValueError('Unexpected telemetry framing')
        end = start + packet_length
        if end > len(data):
            raise ValueError('Truncated telemetry packet')
        frame = data[start:end]
        try:
            message = decoder.parse_char(frame)
        except Exception as exc:
            raise ValueError('Original telemetry packet failed CRC/decode') from exc
        if message is None or message.get_type() == 'BAD_DATA':
            raise ValueError('Original telemetry packet did not decode')
        kind = message.get_type()
        counts[kind] += 1
        expected = copy.deepcopy(message.to_dict())
        payload = frame[header_length:-2]
        replacement = payload
        if kind == 'STATUSTEXT' and old_id.decode() in expected['text']:
            expected['text'] = expected['text'].replace(old_id.decode(), new_id.decode())
            replacement = payload.replace(old_id, new_id)
            fields['STATUSTEXT.text'] += 1
        elif kind == 'AUTOPILOT_VERSION':
            uid = bytes(expected.get('uid2', []))
            prefix_length = len(uid.rstrip(b'\0'))
            if 16 <= prefix_length <= 18 and uid == old_id[:prefix_length] + b'\0' * (18-prefix_length):
                expected['uid2'] = list(new_id[:prefix_length] + b'\0' * (18-prefix_length))
                replacement = payload.replace(old_id[:prefix_length], new_id[:prefix_length])
                fields['AUTOPILOT_VERSION.uid2'] += 1
        if replacement != payload:
            if len(replacement) != len(payload):
                raise ValueError('Identity replacement changed packet length')
            modified = frame[:header_length] + replacement
            crc = mav.x25crc(modified[1:])
            crc.accumulate(bytes([message.crc_extra]))
            frame = modified + struct.pack('<H', crc.crc)
            changed += 1
        try:
            checked = verifier.parse_char(frame)
        except Exception as exc:
            raise ValueError('Derivative telemetry packet failed CRC/decode') from exc
        if checked is None or checked.get_type() == 'BAD_DATA' or not equivalent_fields(checked.to_dict(), expected):
            raise ValueError('Unexpected decoded telemetry field difference')
        if (checked.get_srcSystem(), checked.get_srcComponent(), checked.get_seq()) != (
                message.get_srcSystem(), message.get_srcComponent(), message.get_seq()):
            raise ValueError('Telemetry identity envelope changed')
        output.extend(data[pos:start])
        output.extend(frame)
        pos = end
    result = bytes(output)
    if old_id[:16] in result:
        raise ValueError('Host identifier remains in telemetry')
    return result, {'messages': sum(counts.values()), 'message_counts': dict(counts),
                    'changed_messages': changed, 'changed_fields': dict(fields),
                    'timestamps_headers_lengths_and_other_fields_equal': True,
                    'original_and_derivative_crc_valid': True, 'bad_data': 0}


def compare_dataflash(original, derivative, old_id, new_id):
    """Decode both complete logs and permit only full MSG identity replacements."""
    left = mavutil.mavlink_connection(str(original), robust_parsing=False)
    right = mavutil.mavlink_connection(str(derivative), robust_parsing=False)
    counts, changed = Counter(), 0
    try:
        while True:
            a, b = left.recv_match(), right.recv_match()
            if a is None or b is None:
                if a is not None or b is not None:
                    raise ValueError('DataFlash message count mismatch')
                break
            if a.get_type() == 'BAD_DATA' or b.get_type() == 'BAD_DATA':
                raise ValueError('DataFlash BAD_DATA')
            expected = a.to_dict()
            if a.get_type() == 'MSG' and old_id.decode() in expected['Message']:
                expected['Message'] = expected['Message'].replace(old_id.decode(), new_id.decode())
                changed += 1
            if not equivalent_fields(expected, b.to_dict()):
                raise ValueError('Unexpected decoded DataFlash field difference')
            counts[a.get_type()] += 1
    finally:
        left.close()
        right.close()
    return {'messages': sum(counts.values()), 'message_counts': dict(counts),
            'changed_identity_messages': changed, 'all_other_decoded_fields_equal': True, 'bad_data': 0}


def compare_evaluations(source, destination):
    sys.path.insert(0, str(destination / 'src'))
    from failsafelab.evaluate import evaluate_run
    summary = json.loads((source / 'evidence/full/comparison.json').read_text())
    rows = []
    revised = json.loads((destination / 'scenarios/11-gcs-battery-compound.json').read_text())
    for index, row in enumerate(summary['runs'], 1):
        relative = Path('evidence/full') / row['run']
        left = evaluate_run(source / relative)
        right = evaluate_run(destination / relative)
        if left != right:
            raise ValueError('Original and derivative evaluator outputs differ for ' + row['run'])
        if left['outcome'] != row['outcome']:
            raise ValueError('Original evaluator output differs from recorded outcome for ' + row['run'])
        result = {'run': row['run'], 'outcome': right['outcome'],
                  'complete_evaluator_output_equal': True,
                  'evaluator_output_sha256': digest(json.dumps(right, sort_keys=True).encode())}
        if row['scenario_id'] == revised['id']:
            lrev = evaluate_run(source / relative, revised)
            rrev = evaluate_run(destination / relative, revised)
            if lrev != rrev or rrev['outcome'] != 'PASS':
                raise ValueError('Retrospective replay equivalence failed')
            result['revised_corpus_outcome'] = 'PASS'
            result['complete_revised_evaluator_output_equal'] = True
        rows.append(result)
        print(json.dumps({'stage': 'evaluation', 'completed': index, 'total': len(summary['runs'])}), flush=True)
    return {'runs': rows, 'outcomes': dict(Counter(r['outcome'] for r in rows)),
            'revised_replays_passed': sum(r.get('revised_corpus_outcome') == 'PASS' for r in rows),
            'all_original_and_derivative_evaluator_fields_equal': True}


def refresh_aggregate_references(source, destination, report):
    """Point retained aggregate hash references at their derivative inputs.

    Original hash commitments remain in publication-redaction.json. This only
    changes exact SHA-256 tokens in aggregate JSON reports and JSON-formatted
    captured stdout outside sealed runs.
    It does not change measurements, annotations, results or source pins.
    """
    src, dst = source / 'evidence', destination / 'evidence'
    sources = sorted(p for p in src.rglob('*') if p.is_file())
    source_hashes = {p.relative_to(src).as_posix(): digest(p.read_bytes()) for p in sources}
    candidates = []
    for p in dst.rglob('*'):
        if not p.is_file() or p.suffix not in {'.json', '.txt'}:
            continue
        if p.name == 'publication-redaction.json' or any((parent / 'SHA256SUMS').exists()
                                                        for parent in p.parents if parent.is_relative_to(dst)):
            continue
        if p.suffix == '.txt':
            try:
                json.loads(p.read_text())
            except (UnicodeError, ValueError):
                continue
        candidates.append(p)
    originals = {p: p.read_bytes() for p in candidates}
    changed = set()
    for iteration in range(12):
        mapping = {}
        ambiguous = set()
        for name, old in source_hashes.items():
            current = digest((dst / name).read_bytes())
            if old in mapping and mapping[old] != current:
                ambiguous.add(old)
            mapping[old] = current
        # A JSON report and captured stdout can start identical and temporarily
        # differ after a fresh verification command. Refresh their own inputs
        # first; resolve their shared original hash on the following pass.
        for old in ambiguous:
            del mapping[old]
        updated = False
        for p in candidates:
            # Always transform the initial derivative text, so each original
            # hash resolves directly to the latest referenced derivative.
            data = re.sub(rb'(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])',
                          lambda m: mapping.get(m.group().decode(), m.group().decode()).encode(), originals[p])
            if data != p.read_bytes():
                save(p, data)
                changed.add(p)
                updated = True
        if not updated:
            if any(old.encode() in p.read_bytes() for old in ambiguous for p in candidates):
                raise ValueError('Referenced original hash has divergent derivative copies')
            break
    else:
        raise ValueError('Aggregate hash references did not converge')
    rows = []
    for p in sorted(changed):
        relative = p.relative_to(dst).as_posix()
        rows.append({'file': relative, 'original_sha256': source_hashes[relative],
                     'derivative_sha256': digest(p.read_bytes())})
    report['aggregate_reference_refresh'] = {'method': 'Exact original SHA-256 references remapped to corresponding derivative files; original commitments retained here',
                                             'passes': iteration + 1, 'files': rows}
    # Refresh final derivative commitments after changing aggregate JSON.
    by_name = {r['file']: r for r in report['changed_files']}
    for p in candidates:
        relative = p.relative_to(dst).as_posix()
        original = src / relative
        if not original.exists():
            continue
        data = p.read_bytes()
        if digest(data) != source_hashes[relative]:
            by_name[relative] = {'file': relative, 'original_sha256': source_hashes[relative],
                                 'derivative_sha256': digest(data),
                                 'original_bytes': original.stat().st_size, 'derivative_bytes': len(data)}
    report['changed_files'] = [by_name[k] for k in sorted(by_name)]
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', required=True, type=Path)
    parser.add_argument('--destination-root', required=True, type=Path)
    parser.add_argument('--machine-id-file', type=Path, default=Path('/etc/machine-id'))
    args = parser.parse_args()
    source, destination = args.source_root.resolve(), args.destination_root.resolve()
    if source == destination or source.is_relative_to(destination) or destination.is_relative_to(source):
        raise ValueError('Original and derivative roots must be separate')
    old_id = args.machine_id_file.read_bytes().strip()
    if len(old_id) != 32 or any(c not in b'0123456789abcdef' for c in old_id):
        raise ValueError('Expected a 32-character local machine identifier')
    recorded = json.loads((source / 'evidence/full/4.5.6/01-gcs-loss/schedule-0.0/run.json').read_text())
    old_host = recorded['host']['uname'][1].encode()
    if len(old_host) < 4:
        raise ValueError('Hostname too short for unambiguous text replacement')
    recorded_binary = Path(recorded['command'][0])
    if not recorded_binary.is_absolute() or recorded_binary.name != 'arducopter' or recorded_binary.parents[1].name != 'vendor':
        raise ValueError('Unexpected recorded simulator command path')
    recorded_root = recorded_binary.parents[2]
    if recorded_root.parts[1] not in {'home', 'Users'}:
        raise ValueError('Unsupported recorded home directory layout')
    recorded_home = Path(*recorded_root.parts[:3])
    source_evidence, dest_evidence = source / 'evidence', destination / 'evidence'
    replacements = [(str(recorded_root).encode(), FICTIONAL_ROOT),
                    (str(recorded_home).encode(), b'/home/researcher'),
                    (old_host, FICTIONAL_HOSTNAME)]
    report = {'schema_version': 1, 'scope': 'Public derivative of retained SITL evidence; no new simulation',
              'originals_modified': False, 'original_identifiers_recorded': False,
              'fictional_machine_id': FICTIONAL_MACHINE_ID.decode(),
              'fictional_hostname': FICTIONAL_HOSTNAME.decode(),
              'fictional_recorded_project_root': FICTIONAL_ROOT.decode(),
              'changed_files': [], 'telemetry': [], 'dataflash': [], 'seals': []}
    files = sorted(p for p in source_evidence.rglob('*') if p.is_file())
    original_hashes = {}
    for number, original in enumerate(files, 1):
        relative = original.relative_to(source_evidence)
        target = dest_evidence / relative
        data = original.read_bytes()
        original_hashes[relative.as_posix()] = digest(data)
        if original.name == 'SHA256SUMS':
            continue
        if original.suffix == '.tlog':
            result, details = sanitize_tlog(data, old_id, FICTIONAL_MACHINE_ID)
            report['telemetry'].append({'file': relative.as_posix(), **details})
        elif original.suffix.upper() == '.BIN' and original.parent.name == 'logs':
            result = data.replace(old_id, FICTIONAL_MACHINE_ID)
            if old_id[:16] in result:
                raise ValueError('Partial host identifier remains in DataFlash')
        else:
            result = data
            try:
                data.decode('utf-8')
            except UnicodeDecodeError:
                if any(value in data for value in (old_id[:16], old_host, str(recorded_home).encode())):
                    raise ValueError('Unrecognized binary contains private metadata')
            else:
                result = result.replace(old_id, FICTIONAL_MACHINE_ID)
                for old, new in replacements:
                    result = result.replace(old, new)
        save(target, result)
        if data != result:
            report['changed_files'].append({'file': relative.as_posix(),
                'original_sha256': digest(data), 'derivative_sha256': digest(result),
                'original_bytes': len(data), 'derivative_bytes': len(result)})
        if original.suffix.upper() == '.BIN' and original.parent.name == 'logs':
            details = compare_dataflash(original, target, old_id, FICTIONAL_MACHINE_ID)
            report['dataflash'].append({'file': relative.as_posix(), **details})
            print(json.dumps({'stage': 'dataflash', 'completed': len(report['dataflash']), 'file': relative.as_posix()}), flush=True)
    for original in (p for p in files if p.name == 'SHA256SUMS'):
        relative = original.relative_to(source_evidence)
        target = dest_evidence / relative
        lines = []
        for line in original.read_text().splitlines():
            old_hash, name = line.split('  ', 1)
            member = target.parent / name
            if not member.resolve().is_relative_to(target.parent.resolve()) or not member.is_file():
                raise ValueError('Unsafe or missing seal member')
            lines.append(digest(member.read_bytes()) + '  ' + name)
        new_data = ('\n'.join(lines) + '\n').encode()
        save(target, new_data)
        report['seals'].append({'file': relative.as_posix(), 'scope': 'Derivative bytes only',
                'original_seal_sha256': digest(original.read_bytes()),
                'derivative_seal_sha256': digest(new_data), 'members': len(lines)})
    report['evaluations'] = compare_evaluations(source, destination)
    report['private_identifier_scan'] = {'files_scanned': 0, 'matches': 0}
    for path in dest_evidence.rglob('*'):
        if not path.is_file():
            continue
        data = path.read_bytes()
        report['private_identifier_scan']['files_scanned'] += 1
        if any(value in data for value in (old_id[:16], old_host, str(recorded_home).encode())):
            raise ValueError('Private metadata remains in publication evidence')
    report['original_tree_recheck'] = {'files': len(original_hashes), 'all_original_hashes_unchanged': True}
    for name, expected in original_hashes.items():
        if digest((source_evidence / name).read_bytes()) != expected:
            raise ValueError('Private original changed during derivative creation')
    refresh_aggregate_references(source, destination, report)
    report['complete'] = True
    save(dest_evidence / 'publication-redaction.json', (json.dumps(report, indent=2) + '\n').encode())
    print(json.dumps({'complete': True, 'changed_files': len(report['changed_files']),
                      'telemetry_files': len(report['telemetry']), 'dataflash_files': len(report['dataflash']),
                      'derivative_seals': len(report['seals']), 'outcomes': report['evaluations']['outcomes'],
                      'revised_replays_passed': report['evaluations']['revised_replays_passed']}))


if __name__ == '__main__':
    main()
