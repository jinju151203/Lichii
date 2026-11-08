#!/usr/bin/env python3
"""Install the Ounce vibration query fix into an existing owned-game build, then verify the linked host table."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import tempfile

FIX_ID = 'ocarina-controller-playback-hid-v1'
PUBLIC = '_ZN2nn3hid29IsOunceVibrationDeviceMountedERKNS0_21VibrationDeviceHandleE'
DETAIL = '_ZN2nn3hid6detail29IsOunceVibrationDeviceMountedEPbRKNS0_21VibrationDeviceHandleE'
LEGACY = '_ZN2nn3hid6detail24IsVibrationDeviceMountedEPbRKNS0_21VibrationDeviceHandleE'
ANCHOR = '// Result detail::IsVibrationPermitted(bool *out)'
BODY = '''// Switch 2's mount query uses the same host channel mapping as the existing vibration query.
// Ocarina asks this while starting controller-driven playback; its SDK otherwise opens the unimplemented hid service.
// Behavior reference: seedds/nxnative dm/host/hle_hid.c, blob 8e280577c6c1851524e2b2fc4797d8664de09dcb.
static void ov_vib_mounted_ounce(Cpu *c) {
    const uint32_t *h = need_handle(arg_p(c, 0), "IsOunceVibrationDeviceMounted");
    static volatile int32_t asked;
    once(&asked, "hid: Ounce vibration mount query handled by host (device %#x)", *h);
    ret_x(c, vibration_side(h, "IsOunceVibrationDeviceMounted") >= 0);
}

'''
BINDINGS = f'HOST_OVERRIDE("{PUBLIC}", ov_vib_mounted_ounce);\nHOST_OVERRIDE("{DETAIL}", ov_vib_mounted);'
OLD_BINDING = f'HOST_OVERRIDE("{LEGACY}", ov_vib_mounted);'


def patched_source(raw: bytes) -> bytes:
    text = raw.decode('utf-8')
    newline = '\r\n' if '\r\n' in text else '\n'
    body, bindings = BODY.replace('\n', newline), BINDINGS.replace('\n', newline)
    if body in text and bindings in text:
        return raw
    if PUBLIC in text or DETAIL in text or 'ov_vib_mounted_ounce' in text:
        raise ValueError('다른 Ounce 진동 패치가 이미 있습니다. 기존 코드를 덮어쓰지 않았습니다.')
    if text.count(ANCHOR) != 1 or text.count(OLD_BINDING) != 1:
        raise ValueError('이 수정이 지원하는 ov_input.c 형식과 다릅니다. 기존 코드를 덮어쓰지 않았습니다.')
    return text.replace(ANCHOR, body + ANCHOR).replace(OLD_BINDING, OLD_BINDING + newline + bindings).encode('utf-8')


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def linked_hooks(path: Path) -> dict[str, int]:
    """Read actual x64 PE HOST_OVERRIDE entries, not just strings that might occur elsewhere."""
    if path.stat().st_size > 1024 * 1024 * 1024:
        raise ValueError('실행 파일이 예상 크기를 넘습니다.')
    raw = path.read_bytes()
    try:
        u16 = lambda p: struct.unpack_from('<H', raw, p)[0]
        u32 = lambda p: struct.unpack_from('<I', raw, p)[0]
        u64 = lambda p: struct.unpack_from('<Q', raw, p)[0]
        pe = u32(0x3c)
        if raw[:2] != b'MZ' or raw[pe:pe + 4] != b'PE\0\0' or u16(pe + 4) != 0x8664:
            raise ValueError('Windows x64 실행 파일이 아닙니다.')
        opt = pe + 24
        if u16(opt) != 0x20b:
            raise ValueError('PE32+ 실행 파일이 아닙니다.')
        image_base = u64(opt + 24)
        sections = []
        first = opt + u16(pe + 20)
        for i in range(u16(pe + 6)):
            p = first + 40 * i
            name = raw[p:p + 8].split(b'\0')[0]
            sections.append((name, u32(p + 12), u32(p + 16), u32(p + 20)))
        def file_offset(va):
            rva = va - image_base
            for _, start, size, offset in sections:
                if start <= rva < start + size:
                    return offset + rva - start
            return None
        hooks = {}
        for name, _, size, offset in sections:
            if not name.startswith(b'.ovr') or offset + size > len(raw):
                continue
            for p in range(offset, offset + size - 15, 16):
                name_offset, fn = file_offset(u64(p)), u64(p + 8)
                if name_offset is None or file_offset(fn) is None:
                    continue
                end = raw.find(b'\0', name_offset, name_offset + 256)
                if end < 0:
                    continue
                symbol = raw[name_offset:end].decode('ascii', errors='replace')
                if symbol in (PUBLIC, DETAIL, LEGACY):
                    if symbol in hooks:
                        raise ValueError('중복된 진동 함수 연결이 있습니다.')
                    hooks[symbol] = fn
        if set(hooks) != {PUBLIC, DETAIL, LEGACY} or hooks[DETAIL] != hooks[LEGACY]:
            raise ValueError('오카리나 연주 수정 함수가 실행 파일에 연결되지 않았습니다.')
        return hooks
    except (struct.error, IndexError) as error:
        raise ValueError('실행 파일의 PE 구조를 읽지 못했습니다.') from error


def safe_file(path: Path) -> None:
    for item in (path, *path.parents):
        info = item.lstat()
        if item.is_symlink() or getattr(info, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400):
            raise ValueError('연결된 파일이나 폴더는 변경하지 않습니다: ' + str(item))
    if not path.is_file():
        raise ValueError('필요한 설치 파일이 없습니다: ' + str(path))


def atomic_bytes(path: Path, data: bytes) -> None:
    fd, name = tempfile.mkstemp(prefix='.oot-playback-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def apply(root: Path) -> dict:
    root = root.absolute()
    source = root / 'runtime/ov_input.c'
    out = root / 'build/oot111'
    exe = out / 'ocarina.exe'
    python = root / 'ferramentas/python/python.exe'
    ninja = root / 'ferramentas/bin/ninja.exe'
    needed = [source, exe, python, ninja, root / 'tools/build_game.py', root / 'runtime/host.h',
              root / 'tools/data/expected-oot111.json', root / 'generated/oot111/layout.json',
              root / 'build/exefs/main', root / 'build/romfs/index.json',
              root / 'ferramentas/llvm/bin/clang.exe']
    for path in needed:
        safe_file(path)
    before = source.read_bytes()
    after = patched_source(before)
    receipt = out / 'ocarina-playback-fix.json'
    try:
        linked_hooks(exe)
        already_linked = True
    except ValueError:
        already_linked = False
    if before == after and already_linked:
        return dict(status='already_fixed', fix=FIX_ID, game_exe=str(exe), receipt=str(receipt),
                    message='연주 충돌 수정이 이미 실행 파일에 연결되어 있습니다.')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S-%f')
    backup = out / 'playback-backup' / stamp
    backup.mkdir(parents=True, exist_ok=False)
    shutil.copy2(source, backup / 'ov_input.c')
    shutil.copy2(exe, backup / 'ocarina.exe')
    runtime_object = out / 'obj/runtime/ov_input.o'
    if runtime_object.exists():
        safe_file(runtime_object)
        shutil.copy2(runtime_object, backup / 'ov_input.o')
    log = out / 'ocarina-playback-build.log'
    command = [str(python), 'tools/build_game.py', '--version', 'oot111', '--gen', 'generated/oot111',
               '--out', str(out), '--expected', 'tools/data/expected-oot111.json',
               '--exefs', str(root / 'build/exefs'), '--romfs', str(root / 'build/romfs'), '--jobs', '2',
               '--toolchain', str(root / 'ferramentas/llvm'), '--deps', str(root / 'ferramentas/deps'),
               '--ninja', str(ninja)]
    try:
        atomic_bytes(source, after)
        if runtime_object.exists():
            runtime_object.unlink()  # Invalidate this one runtime object even if the machine's clock moved backwards.
        environment = dict(os.environ, PYTHONUTF8='1', PYTHONUNBUFFERED='1')
        environment['PATH'] = os.pathsep.join([str(root / 'ferramentas/llvm/bin'), str(root / 'ferramentas/bin'),
                                               str(root / 'ferramentas/deps/bin'), environment.get('PATH', '')])
        with log.open('wb') as output:
            built = subprocess.run(command, cwd=root, env=environment, stdout=output, stderr=subprocess.STDOUT,
                                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if built.returncode:
            raise ValueError(f'로컬 컴파일 실패 (코드 {built.returncode}). 로그: {log}')
        hooks = linked_hooks(exe)
        record = dict(fix=FIX_ID, installed_at=datetime.now(timezone.utc).isoformat(),
                      previous_exe_sha256=digest(backup / 'ocarina.exe'), exe_sha256=digest(exe),
                      source_sha256=digest(source), verified_host_symbols=sorted(hooks), backup=str(backup))
        atomic_bytes(receipt, json.dumps(record, ensure_ascii=False, indent=2).encode('utf-8'))
        return dict(status='fixed', fix=FIX_ID, game_exe=str(exe), receipt=str(receipt), build_log=str(log),
                    backup=str(backup), message='컨트롤러 진동 조회 수정과 실행 파일 연결 검사를 완료했습니다.')
    except BaseException:
        atomic_bytes(source, before)
        shutil.copy2(backup / 'ocarina.exe', exe)
        if (backup / 'ov_input.o').exists():
            shutil.copy2(backup / 'ov_input.o', runtime_object)
        elif runtime_object.exists():
            runtime_object.unlink()
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(apply(args.root), ensure_ascii=True))
        return 0
    except (OSError, ValueError) as error:
        print(json.dumps(dict(error=str(error)), ensure_ascii=True))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
