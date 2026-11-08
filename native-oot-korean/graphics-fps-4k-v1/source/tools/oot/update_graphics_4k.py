#!/usr/bin/env python3
"""Transactional source update for an existing owned-game Ocarina native installation."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid

# The installed embeddable Python uses python314._pth and omits the script's folder,
# just like -I. Resolve bundled siblings explicitly before importing either helper.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fix_ocarina_playback import atomic_bytes, digest, linked_hooks, patched_source, safe_file
from patch_generated import DYN_DT, FIXED_RES, upgrade_fixed_resolution

UPDATE_ID = 'oot-graphics-recovery-v2'
# Restore texture lowering after reported scene corruption. The user explicitly wants
# the 300 FPS/4K features and their chosen FPS/resolution settings left in place.
SETTINGS = dict(vk_present='mailbox',
                upscaler='bilinear', sharpness='0', color_preset='default', color_brightness='0',
                color_contrast='100', color_saturation='100', color_gamma='1', perf_overlay='fps')


def normalized(raw: bytes) -> bytes:
    return raw.replace(b'\r\n', b'\n')


def fingerprint(raw: bytes) -> str:
    return hashlib.sha256(normalized(raw)).hexdigest()


def config_update(raw: bytes) -> bytes:
    bom = b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
    text = raw[len(bom):].decode('utf-8')
    newline = '\r\n' if '\r\n' in text else '\n'
    seen = set()
    out = []
    for line in text.splitlines(keepends=True):
        m = re.match(r'^([ \t]*(?:TOTK_)?([a-z0-9_]+)[ \t]*=[ \t]*)([^\r\n]*)(\r?\n)?$', line, re.I)
        if m and m[2].lower() in SETTINGS:
            key = m[2].lower()
            seen.add(key)
            line = m[1] + SETTINGS[key] + (m[4] or '')
        out.append(line)
    text = ''.join(out)
    missing = [key for key in SETTINGS if key not in seen]
    if missing:
        if text and not text.endswith('\n'):
            text += newline
        text += newline + '[display]' + newline
        text += ''.join(f'{key} = {SETTINGS[key]}' + newline for key in missing)
    return bom + text.encode('utf-8')


def launcher_update(raw: bytes) -> bytes:
    # The obsolete Upscaler Test shortcut must not re-enable the path that blackened the user's scene.
    text = raw.decode('utf-8-sig')
    newline = '\r\n' if '\r\n' in text else '\n'
    text = text.replace('\r\n', '\n')
    marker = '# Ocarina graphics recovery v2: safe compute fallback, real-time clock, measured frame logs.'
    if marker in text:
        return raw
    anchor = '$game = Start-Process .\\ocarina.exe'
    if text.count(anchor) != 1:
        raise ValueError('지원되는 기존 실행 스크립트가 아닙니다. 설치 파일을 변경하지 않았습니다.')
    previous = "# Ocarina graphics/fps/4k v1: safe compute fallback and authored real-time clock.\n$env:TOTK_BIG_CS = '1'\n$env:OOT_DYN_DT = '1'\n"
    text = text.replace(previous, '')
    text = text.replace(anchor, marker + "\n$env:TOTK_BIG_CS = '1'\n$env:OOT_DYN_DT = '1'\n$env:TOTK_TRACE = 'perf'\n" + anchor)
    return b'\xef\xbb\xbf' + text.replace('\n', newline).encode('utf-8')


def target_path(root: Path, rel: str, required=True) -> Path:
    path = root / rel
    if path.exists():
        safe_file(path)
    else:
        if required:
            raise ValueError('기존 설치에 필요한 파일이 없습니다: ' + rel)
        for parent in (path.parent, *path.parents):
            if parent.exists() and (parent.is_symlink() or
                getattr(parent.lstat(), 'st_file_attributes', 0) & 0x400):
                raise ValueError('연결된 폴더는 변경하지 않습니다: ' + str(parent))
    return path


def plan(root: Path, bundle: Path) -> dict[str, bytes]:
    manifest = json.loads((bundle / 'manifest.json').read_text())
    changes = {}
    for entry in manifest['files']:
        rel = entry['path']
        if rel.startswith('/') or '..' in Path(rel).parts:
            raise ValueError('Invalid update payload path')
        source = bundle / 'payload' / rel
        data = source.read_bytes()
        if fingerprint(data) != entry['after']:
            raise ValueError('업데이트 압축 파일 검사에 실패했습니다: ' + rel)
        path = target_path(root, rel, required=entry['before'] is not None)
        old = path.read_bytes() if path.exists() else None
        if old is not None and fingerprint(old) == entry['after']:
            continue
        accepted = [entry['before'], *entry.get('accept', [])]
        if (old is not None and fingerprint(old) not in accepted) or (old is None and entry['before'] is not None):
            raise ValueError('지원 버전과 다른 수정이 있습니다. 덮어쓰지 않았습니다: ' + rel)
        if old is not None and b'\r\n' in old:
            data = normalized(data).replace(b'\n', b'\r\n')
        changes[rel] = data
    source = target_path(root, 'runtime/ov_input.c')
    changes['runtime/ov_input.c'] = patched_source(source.read_bytes())
    clock = target_path(root, 'generated/oot111/main/main_0087.c').read_bytes().decode('utf-8')
    if DYN_DT not in clock.replace('\r\n', '\n') or 'fp_op_s(c, FOP_DIV, 8, 1, 0); oot_dyn_dt(c);' not in clock:
        raise ValueError('기존 오카리나 실시간 처리 코드를 확인하지 못했습니다. FPS 제한을 해제하지 않았습니다.')
    generated = target_path(root, 'generated/oot111/main/main_0098.c').read_bytes()
    text = generated.decode('utf-8').replace('\r\n', '\n')
    for hook in ('oot_fixed_res() ||', 'oot_dynres_runs++;', 'oot_fixed_res() ? oot_res_bits'):
        if hook not in text:
            raise ValueError('기존 해상도 처리 코드를 확인하지 못했습니다. 게임 코드를 변경하지 않았습니다.')
    upgraded = upgrade_fixed_resolution(text)
    changes['generated/oot111/main/main_0098.c'] = upgraded.replace('\n', '\r\n' if b'\r\n' in generated else '\n').encode()
    ini = target_path(root, 'build/oot111/totk.ini', required=False)
    changes['build/oot111/totk.ini'] = config_update(ini.read_bytes() if ini.exists() else b'')
    launcher = target_path(root, 'jogar/jogar-ocarina.ps1')
    changes['jogar/jogar-ocarina.ps1'] = launcher_update(launcher.read_bytes())
    return {rel: data for rel, data in changes.items() if not (root / rel).exists() or (root / rel).read_bytes() != data}


def build_command(root: Path):
    return [str(root / 'ferramentas/python/python.exe'), 'tools/build_game.py', '--version', 'oot111',
            '--gen', 'generated/oot111', '--out', str(root / 'build/oot111'),
            '--expected', 'tools/data/expected-oot111.json', '--exefs', str(root / 'build/exefs'),
            '--romfs', str(root / 'build/romfs'), '--jobs', '2', '--toolchain', str(root / 'ferramentas/llvm'),
            '--deps', str(root / 'ferramentas/deps'), '--ninja', str(root / 'ferramentas/bin/ninja.exe')]


def build(root: Path, log: Path):
    env = dict(os.environ, PYTHONUTF8='1', PYTHONUNBUFFERED='1')
    env['PATH'] = os.pathsep.join([str(root / 'ferramentas/llvm/bin'), str(root / 'ferramentas/bin'),
                                  str(root / 'ferramentas/deps/bin'), env.get('PATH', '')])
    with log.open('wb') as output:
        result = subprocess.run(build_command(root), cwd=root, env=env, stdout=output, stderr=subprocess.STDOUT,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise ValueError(f'로컬 컴파일에 실패했습니다. 기존 실행 파일을 복원합니다. 로그: {log}')


def invalidate(root: Path):
    obj = root / 'build/oot111/obj'
    # Runtime headers affect several menu translation units; never reuse a mixed enum/object build.
    if (obj / 'runtime').is_dir():
        for path in (obj / 'runtime').rglob('*.o'):
            safe_file(path)
            path.unlink()
    chunk = obj / 'main/main_0098.o'
    if chunk.exists():
        safe_file(chunk)
        chunk.unlink()


def apply(root: Path, bundle: Path) -> dict:
    root = root.absolute()
    for rel in ('build/oot111/ocarina.exe', 'ferramentas/python/python.exe', 'ferramentas/bin/ninja.exe',
                'ferramentas/llvm/bin/clang.exe', 'tools/data/expected-oot111.json', 'generated/oot111/layout.json',
                'build/exefs/main', 'build/romfs/index.json'):
        target_path(root, rel)
    changes = plan(root, bundle)
    out = root / 'build/oot111'
    exe = out / 'ocarina.exe'
    receipt = out / 'ocarina-graphics-4k-update.json'
    installed = json.loads(receipt.read_text()) if receipt.is_file() else {}
    if not changes and installed.get('update') == UPDATE_ID and installed.get('exe_sha256') == digest(exe):
        linked_hooks(exe)
        return dict(status='already-current', message='이 업데이트가 이미 적용되어 있습니다.', game_exe=str(exe))
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    backup = out / 'graphics-4k-backup' / stamp
    backup.mkdir(parents=True)
    saved = dict(changes)
    # Installer-authored build files also change during compilation; retain them for a complete rollback.
    for rel in ('build/oot111/ocarina.exe', 'build/oot111/modules.c', 'build/oot111/build.ninja',
                'build/oot111/obj/objects.sha256', 'build/oot111/ocarina-graphics-4k-update.json'):
        target_path(root, rel, required=False)
        saved.setdefault(rel, b'')
    existed = []
    for rel in saved:
        path = root / rel
        if path.exists():
            dest = backup / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
            existed.append(rel)
    atomic_bytes(backup / 'backup.json', json.dumps(dict(update=UPDATE_ID, files=list(saved), existed=existed), indent=2).encode())
    log = out / 'ocarina-graphics-4k-build.log'
    try:
        for rel, data in changes.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            atomic_bytes(path, data)
        invalidate(root)
        build(root, log)
        hooks = linked_hooks(exe)
        if 'const int rt_oot_clock = 1;' not in (out / 'modules.c').read_text():
            raise ValueError('실행 파일 빌드의 오카리나 실시간 처리 표시를 확인하지 못했습니다.')
        record = dict(update=UPDATE_ID, installed_at=datetime.now(timezone.utc).isoformat(), backup=str(backup),
                      exe_sha256=digest(exe), changed_files=list(changes), verified_host_symbols=sorted(hooks),
                      settings=SETTINGS, frame_settings_preserved=True,
                      gameplay_verified=False, actual_4k_verified=False, actual_300fps_verified=False)
        atomic_bytes(receipt, json.dumps(record, ensure_ascii=False, indent=2).encode())
        return dict(status='updated', game_exe=str(exe), backup=str(backup), build_log=str(log),
                    message='이전 텍스처 셰이더를 복구했습니다. 기존 FPS·내부 4K 설정을 유지했습니다. 실제 게임 화면은 확인이 필요합니다.')
    except BaseException:
        for rel in saved:
            path = root / rel
            if rel in existed:
                path.parent.mkdir(parents=True, exist_ok=True)
                atomic_bytes(path, (backup / rel).read_bytes())
            elif path.exists():
                path.unlink()
        invalidate(root)
        raise


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--bundle', type=Path, default=Path(__file__).resolve().parent)
    args = ap.parse_args()
    try:
        print(json.dumps(apply(args.root, args.bundle), ensure_ascii=True))
        return 0
    except (OSError, ValueError) as error:
        print(json.dumps(dict(error=str(error)), ensure_ascii=True))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
