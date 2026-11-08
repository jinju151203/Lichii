#!/usr/bin/env python3
"""Build a game-free native EXE that updates an existing Ocarina installation locally."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
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
SOURCE = ['instalador/update-graphics-4k.ps1', 'instalador/graphics-4k-bootstrap.ps1', 'instalador/singlefile.c',
          'tools/oot/package_singlefile.py', 'tools/oot/make_graphics_4k_update.py',
          'tests/oot_graphics_policy_test.py', 'tests/oot_graphics_update_test.py',
          'tests/native_exit_capture.cpp', 'tests/native_exit_capture_test.py',
          'tests/ounce_vibration_test.py', 'tests/ocarina_playback_patch_test.py',
          'runtime/ov_input.c', 'LICENSE', 'LICENSE-MIT', 'THIRD_PARTY_NOTICES.md',
          'docs/oot-graphics-fps-4k.md']


def fingerprint(raw):
    return hashlib.sha256(raw.replace(b'\r\n', b'\n')).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base', type=Path, required=True, help='unmodified Korean ko2 source tree')
    ap.add_argument('--cc', type=Path, required=True)
    ap.add_argument('--windres', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    archive = args.out.with_suffix('.zip')
    manifest = dict(update='oot-graphics-fps-internal4k-v1', upstream='fe7a9399a6daa5a789e7557e5a193db8f3055c2a',
                    lichii_reference='bf4c42e223d4812d4456d3d8f66d892571d19a13', files=[])
    prefix = 'Ocarina-Graphics-4K/'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for rel in PAYLOAD:
            data = (ROOT / rel).read_bytes()
            old = args.base / rel
            manifest['files'].append(dict(path=rel, before=fingerprint(old.read_bytes()) if old.is_file() else None,
                                          after=fingerprint(data)))
            bundle.writestr(prefix + 'payload/' + rel, data)
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
    subprocess.run([sys.executable, str(ROOT / 'tools/oot/package_singlefile.py'), str(archive),
                    '--cc', str(args.cc.absolute()), '--windres', str(args.windres.absolute()),
                    '--out', str(args.out.absolute()), '--graphics-4k'], check=True)


if __name__ == '__main__':
    main()
