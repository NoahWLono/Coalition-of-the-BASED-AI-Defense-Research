#!/usr/bin/env python3
"""Build or verify the complete CEDAR source release using the standard library.

Build: python3 scripts/release.py
Verify: python3 scripts/release.py --verify dist/cedar-portfolio-source.zip
Verification reads bounded ZIP streams without extracting or executing members.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import tempfile
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = 'cedar'
MANIFEST = 'cedar/RELEASE_MANIFEST.json'
INSTRUCTIONS = 'cedar/VERIFY_RELEASE.txt'
EXCLUDED_PARTS = {'.git', '.venv', 'venv', 'runtime', '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', '.cache', '.tox', '.nox', 'node_modules', 'dist', 'tmp'}
EXCLUDED_SUFFIXES = {'.pyc', '.pyo', '.sqlite', '.sqlite3', '.db'}
MAX_ARCHIVE = 1024 * 1024 * 1024
MAX_MEMBER = 512 * 1024 * 1024
MAX_EXPANDED = 2 * 1024 * 1024 * 1024
MAX_FILES = 10000
CHUNK = 1024 * 1024
CORE_FILES = {'README.md', 'LICENSE', 'pyproject.toml', 'uv.lock', 'cedar/__main__.py', 'scripts/release.py', 'docs/THIRD_PARTY.md', 'vendor/LICENSE-CycloneDX'}
VERIFY_TEXT = '''CEDAR source release verification

From a separately trusted checkout, without installing dependencies:
  python3 scripts/release.py --verify /path/to/cedar-portfolio-source.zip

A valid result exits 0 and prints JSON. An invalid archive exits 1. Verification
checks member paths, duplicate names, file types, expansion limits, exact
manifest membership, per-file byte sizes and SHA-256 hashes, and the presence of
core sources, a screenshot, a recording and a decision ZIP. It never extracts or
executes archive members. The script requires only Python's standard library.

Every file is under cedar/. RELEASE_MANIFEST.json hashes every archive file
except itself. The adjacent .zip.sha256 file hashes the complete ZIP and is kept
outside it, avoiding self-referential hashes. ZIP timestamps and permissions are
normalized; identical included file bytes produce identical ZIP bytes.

The release includes deliverable artifacts even if Git ignores them. Recursive
exclusions remove Git metadata, virtual environments, runtime state, caches,
dist/tmp directories, environment files and compiled Python/database files.
Symlinks and special files are rejected. Runtime sessions and credentials must
stay in excluded runtime/environment locations, never in source or artifacts.

Hashes establish internal consistency only. They are not signatures and do not
prove authorship, claim truth, safety, correctness or third-party acceptance.
Use a separately trusted verifier: code supplied by an untrusted archive can
also be replaced. Decision ZIPs have their own evidence verifier:
  python3 scripts/verify_package.py artifacts/full-decision.zip

After verification, extract into a chosen directory and read cedar/README.md.
'''


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')


def excluded(relative):
    parts = PurePosixPath(relative).parts
    return (any(p in EXCLUDED_PARTS or p == '.env' or p.startswith('.env.') for p in parts)
            or any(p in {'.DS_Store', '.coverage'} or p.startswith('.coverage.') for p in parts)
            or PurePosixPath(relative).suffix in EXCLUDED_SUFFIXES)


def safe_name(name):
    parts = PurePosixPath(name).parts
    return (isinstance(name, str) and name.startswith('cedar/') and len(parts) >= 2
            and '\\' not in name and not any(ord(c) < 32 or ord(c) == 127 for c in name)
            and all(p not in {'', '.', '..'} for p in name.split('/'))
            and not any(':' in p for p in parts) and not excluded('/'.join(parts[1:])))


def validate_deliverables(names):
    relative = {name.removeprefix('cedar/') for name in names}
    missing = sorted(CORE_FILES - relative)
    if missing:
        raise ValueError('Missing core release files: ' + ', '.join(missing))
    artifacts = [PurePosixPath(name) for name in relative if name.startswith('artifacts/')]
    groups = {
        'screenshots': sorted(str(p) for p in artifacts if p.suffix.lower() in {'.png', '.jpg', '.jpeg'}),
        'recordings': sorted(str(p) for p in artifacts if p.suffix.lower() in {'.webm', '.mp4'}),
        'decision_packages': sorted(str(p) for p in artifacts if 'decision' in p.name.lower() and p.suffix.lower() == '.zip'),
    }
    for group, members in groups.items():
        if not members:
            raise ValueError('Missing release deliverable: ' + group.replace('_', ' '))
    return groups


def source_files(root):
    found = []
    for base, dirs, names in os.walk(root, followlinks=False):
        base = Path(base)
        retained = []
        for name in sorted(dirs):
            path = base / name
            relative = path.relative_to(root).as_posix()
            if excluded(relative):
                continue
            if path.is_symlink():
                raise ValueError('Symlink directory cannot enter release: ' + relative)
            retained.append(name)
        dirs[:] = retained
        for name in sorted(names):
            path = base / name
            relative = path.relative_to(root).as_posix()
            if excluded(relative) or relative in {'RELEASE_MANIFEST.json', 'VERIFY_RELEASE.txt'}:
                continue
            if path.is_symlink():
                raise ValueError('Symlink file cannot enter release: ' + relative)
            if not path.is_file():
                raise ValueError('Special file cannot enter release: ' + relative)
            archive_name = 'cedar/' + relative
            if not safe_name(archive_name):
                raise ValueError('Unsafe source filename: ' + relative)
            found.append((archive_name, path))
    found.sort()
    if len({name.casefold() for name, _ in found}) != len(found):
        raise ValueError('Source names collide on case-insensitive filesystems')
    if len(found) + 2 > MAX_FILES:
        raise ValueError('Release member count limit exceeded')
    validate_deliverables({name for name, _ in found})
    return found


def zip_info(name, executable=False):
    info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | (0o755 if executable else 0o644)) << 16
    return info


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while data := stream.read(CHUNK):
            digest.update(data)
    return digest.hexdigest()


def build_release(root=ROOT, output=None):
    root = Path(root).resolve()
    output = Path(output or root / 'dist/cedar-portfolio-source.zip').resolve()
    if any(ord(c) < 32 for c in output.name):
        raise ValueError('Unsafe output filename')
    if output.is_relative_to(root) and 'dist' not in output.relative_to(root).parts:
        raise ValueError('Output within the source tree must be inside an excluded dist directory')
    files = source_files(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.cedar-release-', suffix='.tmp', dir=output.parent, delete=False) as handle:
            temporary = Path(handle.name)
        entries = {}
        total = 0
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for name, path in files:
                before = path.stat()
                if before.st_size > MAX_MEMBER:
                    raise ValueError('Release member size limit exceeded: ' + name)
                total += before.st_size
                if total > MAX_EXPANDED:
                    raise ValueError('Release expansion limit exceeded')
                executable = bool(before.st_mode & 0o111)
                digest = hashlib.sha256()
                count = 0
                with path.open('rb') as source, archive.open(zip_info(name, executable), 'w') as dest:
                    opened = os.fstat(source.fileno())
                    if not stat.S_ISREG(opened.st_mode) or (opened.st_ino, opened.st_dev) != (before.st_ino, before.st_dev):
                        raise ValueError('Source changed before packaging: ' + name)
                    while data := source.read(CHUNK):
                        count += len(data)
                        if count > before.st_size or count > MAX_MEMBER:
                            raise ValueError('Source grew during packaging: ' + name)
                        digest.update(data)
                        dest.write(data)
                    after = os.fstat(source.fileno())
                if count != before.st_size or (after.st_mtime_ns, after.st_size) != (before.st_mtime_ns, before.st_size):
                    raise ValueError('Source changed during packaging: ' + name)
                entries[name] = {'sha256': digest.hexdigest(), 'size': count, 'mode': '0755' if executable else '0644'}
            instructions = VERIFY_TEXT.encode('utf-8')
            archive.writestr(zip_info(INSTRUCTIONS), instructions)
            entries[INSTRUCTIONS] = {'sha256': hashlib.sha256(instructions).hexdigest(), 'size': len(instructions), 'mode': '0644'}
            manifest = {'schema_version': 'cedar-source-release-1', 'algorithm': 'sha256', 'root': ARCHIVE_ROOT,
                        'files': entries, 'file_count': len(entries), 'total_bytes': sum(x['size'] for x in entries.values()),
                        'deliverables': validate_deliverables(entries),
                        'integrity_scope': 'File consistency only; no authenticity, correctness or claim-truth guarantee.'}
            archive.writestr(zip_info(MANIFEST), canonical(manifest))
        result = verify_release(temporary)
        if not result['valid']:
            raise ValueError('Generated release failed verification: ' + '; '.join(result['errors']))
        digest = file_hash(temporary)
        os.replace(temporary, output)
        temporary = None
        Path(str(output) + '.sha256').write_text(digest + '  ' + output.name + '\n', encoding='utf-8')
        result.update(archive=str(output), sha256=digest, bytes=output.stat().st_size)
        return result
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def load_manifest(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate manifest field: ' + key)
            result[key] = value
        return result
    def nonfinite(value):
        raise ValueError('Non-finite manifest number: ' + value)
    return json.loads(data.decode('utf-8'), object_pairs_hook=unique, parse_constant=nonfinite)


def verify_release(path):
    errors = []
    result = {'valid': False, 'errors': errors, 'scope': 'Archive and file consistency only; no authenticity or claim-truth guarantee.'}
    try:
        path = Path(path)
        if path.stat().st_size > MAX_ARCHIVE:
            raise ValueError('Release archive size limit exceeded')
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_FILES:
                raise ValueError('Release member count limit exceeded')
            names = [info.filename for info in infos]
            if len(set(names)) != len(names) or len({name.casefold() for name in names}) != len(names):
                raise ValueError('Duplicate release members')
            total = 0
            for info in infos:
                if info.orig_filename != info.filename or not safe_name(info.filename):
                    raise ValueError('Unsafe or excluded release member: ' + repr(info.filename))
                kind = stat.S_IFMT(info.external_attr >> 16)
                if info.is_dir() or kind not in (0, stat.S_IFREG) or info.flag_bits & 1:
                    raise ValueError('Unsupported release member type or encryption')
                if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                    raise ValueError('Unsupported release compression')
                if not 0 <= info.file_size <= MAX_MEMBER:
                    raise ValueError('Release member expansion limit exceeded')
                total += info.file_size
                if total > MAX_EXPANDED:
                    raise ValueError('Release expansion limit exceeded')
            if MANIFEST not in names or INSTRUCTIONS not in names:
                raise ValueError('Missing release manifest or verification instructions')
            if archive.getinfo(MANIFEST).file_size > 16 * CHUNK:
                raise ValueError('Release manifest size limit exceeded')
            manifest = load_manifest(archive.read(MANIFEST))
            if manifest['schema_version'] != 'cedar-source-release-1' or manifest['algorithm'] != 'sha256' or manifest['root'] != ARCHIVE_ROOT:
                raise ValueError('Unsupported release manifest format')
            entries = manifest['files']
            if set(entries) != set(names) - {MANIFEST}:
                errors.append('Release manifest file list differs from archive')
            groups = validate_deliverables(names)
            if manifest.get('deliverables') != groups:
                errors.append('Release deliverable index mismatch')
            counted = 0
            for info in infos:
                if info.filename == MANIFEST:
                    continue
                digest = hashlib.sha256()
                size = 0
                with archive.open(info) as stream:
                    while data := stream.read(CHUNK):
                        size += len(data)
                        if size > info.file_size or size > MAX_MEMBER:
                            raise ValueError('Release member expansion limit exceeded')
                        digest.update(data)
                counted += size
                entry = entries.get(info.filename, {})
                if entry.get('size') != size or entry.get('sha256') != digest.hexdigest():
                    errors.append('Release hash or size mismatch: ' + info.filename)
                mode = '0755' if info.external_attr >> 16 & 0o111 else '0644'
                if entry.get('mode') != mode:
                    errors.append('Release file mode mismatch: ' + info.filename)
            if manifest.get('file_count') != len(infos) - 1 or manifest.get('total_bytes') != counted:
                errors.append('Release manifest counts mismatch')
            result.update(files_checked=len(infos)-1, bytes_checked=counted, deliverables=groups)
    except (ValueError, TypeError, KeyError, AttributeError, UnicodeError, RecursionError, OverflowError, OSError, RuntimeError, zipfile.BadZipFile, zlib.error) as exc:
        errors.append('Invalid source release: ' + str(exc))
    result['valid'] = not errors
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', type=Path, metavar='ZIP', help='Verify an existing source release without extracting or executing files')
    parser.add_argument('--root', type=Path, default=ROOT, help='Source repository; defaults to this script\'s parent repository')
    parser.add_argument('--output', type=Path, help='Output ZIP; defaults to ROOT/dist/cedar-portfolio-source.zip')
    args = parser.parse_args(argv)
    try:
        result = verify_release(args.verify) if args.verify else build_release(args.root, args.output)
    except (OSError, ValueError) as exc:
        result = {'valid': False, 'errors': [str(exc)]}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result['valid'] else 1


if __name__ == '__main__':
    sys.exit(main())
