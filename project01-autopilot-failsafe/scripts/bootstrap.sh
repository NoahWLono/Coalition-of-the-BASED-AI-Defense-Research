#!/usr/bin/env bash
set -euo pipefail
LAB_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
exec timeout --signal=TERM --kill-after=5s 300s python3 - "$LAB_ROOT" <<'PY'
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import urllib.request

root = Path(sys.argv[1])
if sys.version_info < (3, 9):
    raise SystemExit('Bootstrap requires an existing host Python 3.9 or newer')
manifest = json.loads((root / 'manifest.json').read_text())
cache = root / '.bootstrap'
cache.mkdir(exist_ok=True)
if not cache.resolve().is_relative_to(root):
    raise SystemExit('Refusing a bootstrap directory outside the project')
lock = (cache / 'bootstrap.lock').open('w')
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
downloaded = 0
download_cap = manifest['bounds']['download_bytes_per_invocation']

def fail(message):
    raise SystemExit(message)

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def check(path, item):
    if path.is_symlink() or not path.is_file():
        fail(f'Required regular file missing: {path.relative_to(root)}')
    if path.stat().st_size != item['bytes'] or digest(path) != item['sha256']:
        fail(f'Checksum mismatch; preserving rejected file: {path.relative_to(root)}')

def fetch(item, path):
    global downloaded
    if path.exists() or path.is_symlink():
        check(path, item)
        return
    if downloaded + item['bytes'] > download_cap:
        fail('Pinned downloads exceed the 150 MiB invocation limit')
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.parent.resolve().is_relative_to(root):
        fail('Refusing a download destination outside the project')
    temp = path.with_name(path.name + '.part')
    if temp.exists() or temp.is_symlink():
        fail(f'Incomplete download exists; inspect it before retrying: {temp.relative_to(root)}')
    count = 0
    try:
        request = urllib.request.Request(item['url'], headers={'User-Agent': 'failsafelab-bootstrap/1'})
        with urllib.request.urlopen(request, timeout=30) as response, temp.open('xb') as out:
            if not response.url.startswith('https://'):
                fail('Download redirected away from HTTPS')
            length = response.headers.get('Content-Length')
            if length is not None and int(length) != item['bytes']:
                fail(f'Unexpected upstream size for {path.name}')
            while True:
                block = response.read(min(65536, item['bytes'] - count + 1))
                if not block:
                    break
                count += len(block)
                downloaded += len(block)
                if count > item['bytes'] or downloaded > download_cap:
                    fail('Download exceeded a pinned file size or the total download limit')
                out.write(block)
        check(temp, item)
        temp.replace(path)
    except BaseException:
        if temp.is_file() and not temp.is_symlink():
            temp.unlink()
        raise
    print(f'Verified download: {path.relative_to(root)} ({count} bytes)', flush=True)

def run(args, **kwargs):
    return subprocess.run(args, check=True, env=uv_env, cwd=root, **kwargs)

if platform.system() != 'Linux' or platform.machine() != 'x86_64':
    fail('This pinned laboratory supports Linux x86_64 only')
for command in ('uv', 'bwrap', 'ip', 'ss', 'timeout'):
    if not shutil.which(command):
        fail(f'Required host tool is missing: {command}; bootstrap never uses sudo')
uv_version = subprocess.check_output(['uv', '--version'], text=True).split()[1]
if uv_version != manifest['host_tools']['uv']['tested_version']:
    fail(f"Expected uv {manifest['host_tools']['uv']['tested_version']}; found {uv_version}")
uv_env = dict(os.environ, UV_CACHE_DIR=str(cache / 'uv-cache'),
              UV_PYTHON_INSTALL_DIR=str(cache / 'python'),
              UV_PYTHON_BIN_DIR=str(cache / 'bin'), UV_NO_CONFIG='1',
              UV_PYTHON_DOWNLOADS='never', UV_OFFLINE='1')
for item in manifest['files']:
    path = root / item['path']
    if 'url' in item and item.get('download_if_missing', False):
        fetch(item, path)
    else:
        check(path, item)
    if item.get('executable'):
        path.chmod(path.stat().st_mode | 0o111)
source = manifest['source_evidence']
check(root / source['path'], source)
for item in json.loads((root / source['path']).read_text()):
    check(root / 'docs/source-evidence' / item['version'] / item['path'], item)

requirements = {line.strip() for line in (root / 'requirements.txt').read_text().splitlines()
                if line.strip() and not line.lstrip().startswith('#')}
expected = {f"{item['package']}=={item['version']}" for item in manifest['python']['wheels']}
if requirements != expected:
    fail('requirements.txt differs from the manifest dependency pins')
venv = root / '.venv'
if venv.is_symlink():
    fail('Refusing a symlink for the project virtual environment')
python = venv / 'bin/python'
pin = manifest['python']['version']
if venv.exists():
    if not python.exists():
        fail('Existing .venv is incomplete; inspect it before retrying')
    actual = subprocess.check_output([str(python), '-c', 'import platform; print(platform.python_version())'], text=True).strip()
    if actual != pin:
        fail(f'Existing .venv has Python {actual}; expected {pin}; preserving it')
else:
    # Discover an existing interpreter without changing the user's uv directories.
    discovery = subprocess.run(['uv', '--no-config', 'python', 'find', '--system',
                                '--no-python-downloads', f'cpython@{pin}'],
                               cwd=root, text=True, capture_output=True,
                               env={**os.environ, 'UV_PYTHON_DOWNLOADS': 'never', 'UV_OFFLINE': '1',
                                    'UV_CACHE_DIR': str(cache / 'uv-cache')})
    interpreter = discovery.stdout.strip() if discovery.returncode == 0 else None
    if os.environ.get('LAB_BOOTSTRAP_LOCAL_PYTHON') == '1':
        interpreter = None
    if interpreter:
        interpreter = str(Path(interpreter).resolve())
    else:
        archive = manifest['python']['fallback_archive']
        archive_path = cache / 'python-mirror' / archive['mirror_path']
        fetch(archive, archive_path)
        # uv reads only the verified local mirror; it cannot fetch another build.
        install_env = {**uv_env, 'UV_PYTHON_DOWNLOADS': 'manual'}
        subprocess.run(['uv', '--no-config', 'python', 'install', f'cpython@{pin}',
                        '--mirror', (cache / 'python-mirror').as_uri(),
                        '--install-dir', str(cache / 'python'), '--no-bin', '--no-registry',
                        '--offline'], cwd=root, env=install_env, check=True)
        interpreter = str(cache / 'python' / f'cpython-{pin}-linux-x86_64-gnu/bin/python3.12')
    run(['uv', '--no-config', 'venv', '--python', interpreter, '--no-python-downloads', str(venv)])

wheel_dir = cache / 'wheels'
for item in manifest['python']['wheels']:
    fetch(item, wheel_dir / item['filename'])
wheel_check = '''
import importlib.metadata, json, pathlib, sys, zipfile
root = pathlib.Path(sys.argv[1])
manifest = json.loads((root / 'manifest.json').read_text())
changed = []
for item in manifest['python']['wheels']:
    name = item['package']
    try:
        dist = importlib.metadata.distribution(name)
        if dist.version != item['version']:
            changed.append(name)
            continue
        with zipfile.ZipFile(root / '.bootstrap/wheels' / item['filename']) as wheel:
            for member in wheel.namelist():
                if member.endswith('/') or '.data/' in member or member.endswith('.dist-info/RECORD'):
                    continue
                installed = pathlib.Path(dist.locate_file(member))
                if not installed.is_file() or installed.read_bytes() != wheel.read(member):
                    changed.append(name)
                    break
    except importlib.metadata.PackageNotFoundError:
        changed.append(name)
print(json.dumps(changed))
'''
changed = json.loads(run([str(python), '-c', wheel_check, str(root)],
                         capture_output=True, text=True).stdout)
locked = cache / 'requirements.lock'
locked.write_text(''.join(f"{i['package']}=={i['version']} --hash=sha256:{i['sha256']}\n"
                          for i in manifest['python']['wheels']))
sync = ['uv', '--no-config', 'pip', 'sync', '--python', str(python), '--offline', '--no-index',
        '--no-build', '--require-hashes', '--find-links', str(wheel_dir), str(locked)]
for name in changed:
    sync.extend(['--reinstall-package', name])
run(sync)
if json.loads(run([str(python), '-c', wheel_check, str(root)], capture_output=True, text=True).stdout):
    fail('Installed package contents differ from the pinned wheels')
run([str(python), '-c',
     "import importlib.metadata,json,platform; "
     "print(json.dumps({'python':platform.python_version(),'packages':{n:importlib.metadata.version(n) "
     "for n in ('pymavlink','lxml','fastcrc')}},sort_keys=True))"])
subprocess.run(['bwrap', '--unshare-user', '--unshare-net', '--unshare-pid', '--unshare-ipc',
                '--unshare-uts', '--die-with-parent', '--new-session', '--ro-bind', '/', '/',
                '--dev', '/dev', '--proc', '/proc', '--tmpfs', '/tmp', '/bin/true'], check=True)
print(f'Bootstrap verified; downloaded {downloaded} bytes; namespace preflight passed.', flush=True)
PY
