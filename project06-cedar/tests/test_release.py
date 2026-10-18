"""Source release tests use a small fixture, never the live release directory."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/release.py'


def release():
    assert SCRIPT.exists(),'Source release packager must exist'
    spec=importlib.util.spec_from_file_location('cedar_release',SCRIPT)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def fixture(tmp_path):
    root=tmp_path/'source';root.mkdir()
    files={
        'README.md':'Read me','LICENSE':'MIT fixture','pyproject.toml':'[project]',
        'uv.lock':'lock','cedar/__main__.py':'pass','scripts/release.py':'pass',
        'docs/THIRD_PARTY.md':'Licenses','vendor/LICENSE-CycloneDX':'Apache fixture',
        'artifacts/screenshots/overview.png':'screenshot','artifacts/demo.webm':'recording',
        'artifacts/full-decision.zip':'decision','artifacts/check.log':'evidence log',
        'tests/test_example.py':'pass','.gitignore':'artifacts/*.zip',
        '.git/config':'private','.venv/secret':'private','runtime/state.sqlite':'private',
        'nested/dist/old.zip':'old','nested/__pycache__/x.pyc':'cache','tmp/render.png':'intermediate','nested/tmp/file':'intermediate',
        '.env':'private','nested/.env.local':'private','dist/old.zip':'old',
    }
    for name,text in files.items():
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
    return root


def test_release_includes_ignored_deliverables_and_excludes_private_runtime(tmp_path):
    module=release();root=fixture(tmp_path);out=tmp_path/'release.zip'
    result=module.build_release(root,out)
    assert result['valid']
    with zipfile.ZipFile(out) as archive:
        names=set(archive.namelist())
        assert {'cedar/artifacts/demo.webm','cedar/artifacts/full-decision.zip','cedar/artifacts/check.log','cedar/artifacts/screenshots/overview.png','cedar/vendor/LICENSE-CycloneDX'}<=names
        assert not any(part in {'.git','.venv','runtime','__pycache__','dist','tmp'} or part.startswith('.env') for name in names for part in name.split('/'))
        manifest=json.loads(archive.read('cedar/RELEASE_MANIFEST.json'))
        assert set(manifest['files'])==names-{'cedar/RELEASE_MANIFEST.json'}
        for name,entry in manifest['files'].items():
            assert hashlib.sha256(archive.read(name)).hexdigest()==entry['sha256']
        assert 'cedar/RELEASE_MANIFEST.json' not in manifest['files']
    assert module.verify_release(out)['valid']
    assert Path(str(out)+'.sha256').is_file()


def test_release_reproducible_for_identical_source(tmp_path):
    module=release();root=fixture(tmp_path)
    first=tmp_path/'first.zip';second=tmp_path/'second.zip'
    module.build_release(root,first);module.build_release(root,second)
    assert first.read_bytes()==second.read_bytes()


def test_release_rejects_missing_recording(tmp_path):
    module=release();root=fixture(tmp_path);(root/'artifacts/demo.webm').unlink()
    with pytest.raises(ValueError,match='recording'):
        module.build_release(root,tmp_path/'release.zip')


def test_release_rejects_symlink_in_source(tmp_path):
    module=release();root=fixture(tmp_path);(root/'docs/leak').symlink_to('/etc/passwd')
    with pytest.raises(ValueError,match='[Ss]ymlink'):
        module.build_release(root,tmp_path/'release.zip')


def test_release_verification_detects_tampering_and_unsafe_names(tmp_path):
    module=release();root=fixture(tmp_path);out=tmp_path/'release.zip';module.build_release(root,out)
    with zipfile.ZipFile(out) as archive:files={n:archive.read(n) for n in archive.namelist()}
    files['cedar/README.md']+=b'changed'
    with zipfile.ZipFile(out,'w') as archive:
        for n,b in files.items():archive.writestr(n,b)
    result=module.verify_release(out)
    assert not result['valid'] and any('hash' in e.lower() for e in result['errors'])
    with zipfile.ZipFile(out,'a') as archive:archive.writestr('cedar/../outside',b'escape')
    assert not module.verify_release(out)['valid']


def test_release_cli_verify_stdlib_exit_codes(tmp_path):
    module=release();root=fixture(tmp_path);out=tmp_path/'release.zip';module.build_release(root,out)
    good=subprocess.run([sys.executable,'-I',str(SCRIPT),'--verify',str(out)],capture_output=True,text=True)
    assert good.returncode==0 and json.loads(good.stdout)['valid']
    out.write_bytes(b'not a zip')
    bad=subprocess.run([sys.executable,'-I',str(SCRIPT),'--verify',str(out)],capture_output=True,text=True)
    assert bad.returncode==1 and not json.loads(bad.stdout)['valid']
