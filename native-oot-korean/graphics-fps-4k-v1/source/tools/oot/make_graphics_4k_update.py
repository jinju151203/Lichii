#!/usr/bin/env python3
"""Build a game-free native EXE that updates an existing Ocarina installation locally."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
PAYLOAD = [
    'runtime/frame_rate.c', 'runtime/oot_render_policy.c', 'runtime/oot_render_policy.h',
    'runtime/nvn_api_obj.c', 'runtime/vk_exec_draw.c', 'runtime/cfg.c',
    'runtime/ui/menu.cpp', 'runtime/ui_text.h', 'runtime/ui_text.c', 'runtime/ui_text_ko.inc',
    'runtime/third_party/eglantine/shader_recompiler/frontend/ampere/register_pressure.h',
    'runtime/third_party/eglantine/shader_recompiler/frontend/ampere/lower_to_maxwell.h',
    'runtime/third_party/eglantine/shader_recompiler/frontend/ampere/program_capture.h',
    'tools/build_game.py', 'tools/oot/patch_generated.py',
]
HELPERS = ['update_graphics_4k.py', 'fix_ocarina_playback.py', 'patch_generated.py']
RECOVERY_SHADERS = {
    'runtime/third_party/eglantine/shader_recompiler/frontend/ampere/register_pressure.h',
    'runtime/third_party/eglantine/shader_recompiler/frontend/ampere/lower_to_maxwell.h',
}
SOURCE = ['instalador/update-graphics-4k.ps1', 'instalador/graphics-4k-bootstrap.ps1', 'instalador/singlefile.c',
          'tools/oot/package_singlefile.py', 'tools/oot/make_graphics_4k_update.py',
          'tests/oot_graphics_policy_test.py', 'tests/oot_graphics_update_test.py',
          'tests/native_exit_capture.cpp', 'tests/native_exit_capture_test.py',
          'tests/ounce_vibration_test.py', 'tests/ocarina_playback_patch_test.py',
          'runtime/ov_input.c', 'LICENSE', 'LICENSE-MIT', 'THIRD_PARTY_NOTICES.md',
          'docs/oot-graphics-fps-4k.md']


def fingerprint(raw):
    return hashlib.sha256(raw.replace(b'\r\n', b'\n')).hexdigest()


def payload_entries(base):
    """Ship the previous ko2 texture lowering, accepting either ko2 or the known v1 update on disk.

    The experimental backports remain in the development tree for investigation, not in this recovery payload.
    """
    for rel in PAYLOAD:
        previous = (base / rel).read_bytes() if (base / rel).is_file() else None
        experimental = (ROOT / rel).read_bytes()
        data = previous if rel in RECOVERY_SHADERS else experimental
        if data is None:
            raise ValueError('Required recovery shader is missing from the ko2 baseline: ' + rel)
        entry = dict(path=rel, before=fingerprint(previous) if previous is not None else None,
                     after=fingerprint(data))
        if fingerprint(experimental) != entry['after']:
            entry['accept'] = [fingerprint(experimental)]
        yield entry, data


def verify_bundled_helpers(archive):
    """The installed embeddable Python also omits the script directory. Exercise the real ZIP with -I."""
    with tempfile.TemporaryDirectory(prefix='oot-graphics-isolated-') as temp:
        folder = Path(temp)
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(folder)
        script = folder / 'Ocarina-Graphics-4K/update_graphics_4k.py'
        for arguments, expected in ((['--help'], 0), (['--root', str(folder / 'missing-install')], 1)):
            result = subprocess.run([sys.executable, '-I', str(script), *arguments], cwd=folder,
                                    capture_output=True, text=True, timeout=30)
            if result.returncode != expected or 'Traceback' in result.stderr:
                raise ValueError('Bundled helper failed under isolated Python: ' + result.stdout + result.stderr)
            if expected and not json.loads(result.stdout).get('error'):
                raise ValueError('Bundled helper did not reach installation validation')
    print('PASS: actual bundled helpers load under isolated Python; installation preflight reached')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base', type=Path, required=True, help='unmodified Korean ko2 source tree')
    ap.add_argument('--cc', type=Path, required=True)
    ap.add_argument('--windres', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    archive = args.out.with_suffix('.zip')
    manifest = dict(update='oot-graphics-recovery-v2', profile='previous-ko2-texture-lowering',
                    upstream='fe7a9399a6daa5a789e7557e5a193db8f3055c2a',
                    lichii_reference='bf4c42e223d4812d4456d3d8f66d892571d19a13', files=[])
    prefix = 'Ocarina-Graphics-4K/'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for entry, data in payload_entries(args.base):
            manifest['files'].append(entry)
            bundle.writestr(prefix + 'payload/' + entry['path'], data)
        bundle.writestr(prefix + 'manifest.json', json.dumps(manifest, indent=2))
        for name in HELPERS:
            bundle.write(ROOT / 'tools/oot' / name, prefix + name)
        wrapper = (ROOT / 'instalador/update-graphics-4k.ps1').read_text(encoding='utf-8-sig')
        bundle.writestr(prefix + 'update-graphics-4k.ps1', b'\xef\xbb\xbf' + wrapper.replace('\n', '\r\n').encode())
        for rel in SOURCE + ['tools/oot/' + name for name in HELPERS]:
            bundle.write(ROOT / rel, prefix + 'source/' + rel)
        bundle.write(ROOT / 'docs/oot-graphics-fps-4k.md', prefix + 'README_KO.md')
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
    verify_bundled_helpers(archive)
    subprocess.run([sys.executable, str(ROOT / 'tools/oot/package_singlefile.py'), str(archive),
                    '--cc', str(args.cc.absolute()), '--windres', str(args.windres.absolute()),
                    '--out', str(args.out.absolute()), '--graphics-4k'], check=True)


if __name__ == '__main__':
    main()
