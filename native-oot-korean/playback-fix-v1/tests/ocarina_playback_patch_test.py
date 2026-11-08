#!/usr/bin/env python3
"""Authored PE records and temporary install fixtures: no game executables, saves or generated game code."""
import importlib.util
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('playback_fix', ROOT / 'tools/oot/fix_ocarina_playback.py')
fix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fix)


def authored_pe(hooks=True, broken_alias=False):
    raw = bytearray(0xc00)
    def word(offset, value): struct.pack_into('<H', raw, offset, value)
    def dword(offset, value): struct.pack_into('<I', raw, offset, value)
    def qword(offset, value): struct.pack_into('<Q', raw, offset, value)
    raw[:2] = b'MZ'; dword(0x3c, 0x80); raw[0x80:0x84] = b'PE\0\0'
    word(0x84, 0x8664); word(0x86, 3); word(0x94, 0xf0)
    word(0x98, 0x20b); qword(0xb0, 0x140000000)
    for index, (name, rva, offset) in enumerate([(b'.text', 0x1000, 0x400), (b'.ovr', 0x2000, 0x600), (b'.rdata', 0x3000, 0x800)]):
        pos = 0x188 + 40 * index
        raw[pos:pos + len(name)] = name; dword(pos + 8, 0x200); dword(pos + 12, rva)
        dword(pos + 16, 0x200); dword(pos + 20, offset)
    string = 0x800
    for index, symbol in enumerate((fix.LEGACY, fix.PUBLIC, fix.DETAIL)):
        data = symbol.encode() + b'\0'
        raw[string:string + len(data)] = data
        if hooks or index == 0:
            qword(0x600 + index * 16, 0x140003000 + string - 0x800)
            qword(0x608 + index * 16, 0x140001000 + (16 if index == 1 or index == 2 and broken_alias else 0))
        string += len(data)
    return bytes(raw)


class PlaybackFixTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / '기존 설치 폴더'
        current = (ROOT / 'runtime/ov_input.c').read_bytes()
        self.original = current.replace(fix.BODY.encode(), b'').replace(b'\n' + fix.BINDINGS.encode(), b'')
        self.fixed = current

    def tearDown(self):
        self.temp.cleanup()

    def fixture(self):
        files = ['runtime/ov_input.c', 'runtime/host.h', 'build/oot111/ocarina.exe',
                 'ferramentas/python/python.exe', 'ferramentas/bin/ninja.exe', 'ferramentas/llvm/bin/clang.exe',
                 'tools/build_game.py', 'tools/data/expected-oot111.json', 'generated/oot111/layout.json',
                 'build/exefs/main', 'build/romfs/index.json', 'build/oot111/obj/runtime/ov_input.o']
        for name in files:
            path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'authored fixture')
        (self.root / 'runtime/ov_input.c').write_bytes(self.original)
        (self.root / 'build/oot111/ocarina.exe').write_bytes(authored_pe(False))
        for name in ['build/oot111/totk.ini', 'perfil/save/fixture/progress.sav']:
            path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'untouched authored sentinel')

    def test_source_patch_preserves_every_other_byte_and_line_endings(self):
        for newline in (b'\n', b'\r\n'):
            original = self.original.replace(b'\n', newline)
            fixed = self.fixed.replace(b'\n', newline)
            self.assertEqual(fix.patched_source(original), fixed)
            self.assertEqual(fix.patched_source(fixed), fixed)

    def test_unknown_duplicate_or_partial_sources_are_rejected(self):
        for raw in [b'unknown', self.original + fix.OLD_BINDING.encode(), self.original + fix.PUBLIC.encode()]:
            with self.assertRaises(ValueError): fix.patched_source(raw)

    def test_linked_host_entries_required_not_just_strings(self):
        exe = Path(self.temp.name) / 'fixture.exe'
        for raw, valid in [(authored_pe(), True), (authored_pe(False), False), (authored_pe(True, True), False), (b'MZ', False)]:
            exe.write_bytes(raw)
            if valid: self.assertEqual(set(fix.linked_hooks(exe)), {fix.PUBLIC, fix.DETAIL, fix.LEGACY})
            else:
                with self.assertRaises(ValueError): fix.linked_hooks(exe)

    def test_success_backup_targeted_rebuild_and_idempotence(self):
        self.fixture()
        def build(command, **kwargs):
            self.assertEqual(kwargs['cwd'], self.root)
            self.assertIn('--jobs', command)
            self.assertFalse((self.root / 'build/oot111/obj/runtime/ov_input.o').exists())
            (self.root / 'build/oot111/ocarina.exe').write_bytes(authored_pe())
            return subprocess.CompletedProcess(command, 0)
        with patch.object(fix.subprocess, 'run', side_effect=build) as run:
            result = fix.apply(self.root)
            self.assertEqual(result['status'], 'fixed')
            self.assertEqual(fix.apply(self.root)['status'], 'already_fixed')
            self.assertEqual(run.call_count, 1)
        backup = Path(result['backup'])
        self.assertEqual((backup / 'ov_input.c').read_bytes(), self.original)
        self.assertEqual((backup / 'ocarina.exe').read_bytes(), authored_pe(False))
        for name in ['build/oot111/totk.ini', 'perfil/save/fixture/progress.sav']:
            self.assertEqual((self.root / name).read_bytes(), b'untouched authored sentinel')

    def test_build_or_link_verification_failure_rolls_back(self):
        for bad_link in (False, True):
            self.fixture()
            def fail(command, **kwargs):
                (self.root / 'build/oot111/ocarina.exe').write_bytes(authored_pe(False) if bad_link else b'partial link')
                (self.root / 'build/oot111/obj/runtime/ov_input.o').write_bytes(b'new runtime object')
                return subprocess.CompletedProcess(command, 0 if bad_link else 1)
            with patch.object(fix.subprocess, 'run', side_effect=fail):
                with self.assertRaises(ValueError): fix.apply(self.root)
            self.assertEqual((self.root / 'runtime/ov_input.c').read_bytes(), self.original)
            self.assertEqual((self.root / 'build/oot111/ocarina.exe').read_bytes(), authored_pe(False))
            self.assertEqual((self.root / 'build/oot111/obj/runtime/ov_input.o').read_bytes(), b'authored fixture')


if __name__ == '__main__':
    unittest.main()
