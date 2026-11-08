"""Test real update planning, backups and rollback with authored installation/PE fixtures, no game."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/oot'))
import update_graphics_4k as update
from ocarina_playback_patch_test import authored_pe


class GraphicsUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / '기존 설치 폴더'
        self.bundle = Path(self.temp.name) / 'bundle'
        self.bundle.mkdir()
        base = Path(os.environ.get('OOT_KO2_BASE', ROOT.parent / 'graphics-installed-base'))
        self.base = base
        # Production payload, with its real baseline guard; the caller may provide another Korean baseline.
        import make_graphics_4k_update as package
        manifest = dict(files=[])
        for entry, after in package.payload_entries(base):
            rel = entry['path']
            before = base / rel
            self.put_bundle('payload/' + rel, after)
            manifest['files'].append(entry)
            if before.exists():
                self.put(rel, before.read_bytes())
        self.put_bundle('manifest.json', json.dumps(manifest).encode())
        for rel in ('ferramentas/python/python.exe', 'ferramentas/bin/ninja.exe', 'ferramentas/llvm/bin/clang.exe',
                    'tools/data/expected-oot111.json', 'generated/oot111/layout.json', 'build/exefs/main',
                    'build/romfs/index.json'):
            self.put(rel, b'authored-fixture')
        self.put('runtime/ov_input.c', (base / 'runtime/ov_input.c').read_bytes())
        self.put('generated/oot111/main/main_0087.c', (update.DYN_DT + '\nfp_op_s(c, FOP_DIV, 8, 1, 0); oot_dyn_dt(c);\n').encode())
        import patch_generated as pg
        self.put('generated/oot111/main/main_0098.c', (pg.FIXED_RES_V1 + '\n// authored anchors: oot_fixed_res() || oot_dynres_runs++; oot_fixed_res() ? oot_res_bits\n').encode())
        self.put('jogar/jogar-ocarina.ps1', (base / 'jogar/jogar-ocarina.ps1').read_bytes())
        self.ini = b'\xef\xbb\xbf[language]\r\nlang = ko\r\nmenu_lang = ko\r\n[display]\r\nfps_limit=60\r\nTOTK_FPS_LIMIT=144\r\nvk_dyn_a2c=0\r\n[controls]\r\npad_layout=xbox\r\n'
        self.put('build/oot111/totk.ini', self.ini)
        self.put('build/oot111/ocarina.exe', authored_pe(False))
        self.put('build/oot111/obj/runtime/old.o', b'old object')
        self.put('perfil/save.bin', b'unchanged save')

    def tearDown(self):
        self.temp.cleanup()

    def put(self, rel, data):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def put_bundle(self, rel, data):
        p = self.bundle / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def built(self, root, log):
        self.put('build/oot111/ocarina.exe', authored_pe(True))
        self.put('build/oot111/modules.c', b'const int rt_oot_clock = 1;\n')
        log.write_text('authored build success')

    def test_success_and_idempotence(self):
        with patch.object(update, 'build', side_effect=self.built) as compile:
            result = update.apply(self.root, self.bundle)
            self.assertEqual(result['status'], 'updated')
            self.assertEqual(update.apply(self.root, self.bundle)['status'], 'already-current')
            self.assertEqual(compile.call_count, 1)
        self.assertEqual((self.root / 'perfil/save.bin').read_bytes(), b'unchanged save')
        ini = (self.root / 'build/oot111/totk.ini').read_bytes()
        self.assertIn(b'lang = ko\r\n', ini)
        self.assertIn(b'vk_dyn_a2c=0\r\n', ini)
        self.assertIn(b'pad_layout=xbox\r\n', ini)
        self.assertIn(b'fps_limit=60\r\nTOTK_FPS_LIMIT=144', ini)
        self.assertNotIn(b'oot_resolution', ini)
        self.assertEqual((Path(result['backup']) / 'build/oot111/totk.ini').read_bytes(), self.ini)

    def test_user_300fps_and_4k_settings_are_preserved_byte_for_byte(self):
        for text in (b'fps_limit=300\noot_resolution=4k\n',
                     b'TOTK_FPS_LIMIT = 300\r\nTOTK_OOT_RESOLUTION = 4k\r\n',
                     b'FPS_LIMIT=unlimited\nOOT_RESOLUTION=4k'):
            after = update.config_update(text)
            self.assertTrue(after.startswith(text), (text, after))
            self.assertEqual(update.config_update(after), after)
        self.assertNotIn('fps_limit', update.SETTINGS)
        self.assertNotIn('oot_resolution', update.SETTINGS)

    def v1_fixture(self):
        import make_graphics_4k_update as package
        for rel in package.PAYLOAD:
            self.put(rel, (ROOT / rel).read_bytes())
        self.put('runtime/ov_input.c', (ROOT / 'runtime/ov_input.c').read_bytes())
        self.put('build/oot111/ocarina.exe', authored_pe(True))
        self.put('build/oot111/totk.ini', b'lang=ko\nmenu_lang=ko\nfps_limit=unlimited\noot_resolution=4k\n')
        launcher = (self.root / 'jogar/jogar-ocarina.ps1').read_text(encoding='utf-8-sig')
        block = "# Ocarina graphics/fps/4k v1: safe compute fallback and authored real-time clock.\n$env:TOTK_BIG_CS = '1'\n$env:OOT_DYN_DT = '1'\n"
        self.put('jogar/jogar-ocarina.ps1', (launcher.replace('$game = Start-Process', block + '$game = Start-Process')).encode())

    def test_existing_v1_recovers_exact_previous_texture_headers(self):
        self.v1_fixture()
        import make_graphics_4k_update as package
        original = {rel: (self.root / rel).read_bytes() for rel in package.RECOVERY_SHADERS}
        with patch.object(update, 'build', side_effect=self.built):
            result = update.apply(self.root, self.bundle)
        for rel in package.RECOVERY_SHADERS:
            self.assertEqual((self.root / rel).read_bytes(), (self.base / rel).read_bytes())
            self.assertEqual((Path(result['backup']) / rel).read_bytes(), original[rel])
        ini = (self.root / 'build/oot111/totk.ini').read_text()
        self.assertIn('oot_resolution=4k', ini)
        self.assertIn('fps_limit=unlimited', ini)
        self.assertNotIn('fps_limit=60', ini)
        launcher = (self.root / 'jogar/jogar-ocarina.ps1').read_text(encoding='utf-8-sig')
        self.assertNotIn('# Ocarina graphics/fps/4k v1:', launcher)
        self.assertIn("$env:TOTK_TRACE = 'perf'", launcher)
        self.assertEqual((self.root / 'perfil/save.bin').read_bytes(), b'unchanged save')

    def test_failed_v1_recovery_restores_v1_instead_of_leaving_mixed_sources(self):
        self.v1_fixture()
        import make_graphics_4k_update as package
        paths = [*package.RECOVERY_SHADERS, 'build/oot111/totk.ini', 'build/oot111/ocarina.exe', 'jogar/jogar-ocarina.ps1']
        original = {rel: (self.root / rel).read_bytes() for rel in paths}
        with patch.object(update, 'build', side_effect=ValueError('authored build failure')):
            with self.assertRaises(ValueError):
                update.apply(self.root, self.bundle)
        for rel in paths:
            self.assertEqual((self.root / rel).read_bytes(), original[rel])

    def test_failure_restores_source_settings_exe_and_removes_new_files(self):
        for failure in ('compile', 'host-table', 'metadata'):
            before = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
            def fail(root, log):
                self.built(root, log)
                if failure == 'compile':
                    raise ValueError('authored compiler failure')
                if failure == 'host-table':
                    self.put('build/oot111/ocarina.exe', authored_pe(False))
                if failure == 'metadata':
                    self.put('build/oot111/modules.c', b'no clock flag')
            with patch.object(update, 'build', side_effect=fail):
                with self.assertRaises(ValueError):
                    update.apply(self.root, self.bundle)
            for rel, data in before.items():
                if rel.startswith('build/oot111/graphics-4k-backup/') or '/obj/' in rel or rel.endswith('.log'):
                    continue
                self.assertEqual((self.root / rel).read_bytes(), data, rel)
            self.assertFalse((self.root / 'runtime/oot_render_policy.c').exists())
            self.assertFalse((self.root / 'build/oot111/ocarina-graphics-4k-update.json').exists())

    def test_unknown_source_rejected_without_changes(self):
        p = self.root / 'runtime/frame_rate.c'
        p.write_bytes(p.read_bytes() + b'\n// unknown local change\n')
        before = p.read_bytes()
        with self.assertRaisesRegex(ValueError, '덮어쓰지'):
            update.apply(self.root, self.bundle)
        self.assertEqual(p.read_bytes(), before)
        self.assertEqual((self.root / 'build/oot111/totk.ini').read_bytes(), self.ini)
        self.assertFalse((self.root / 'build/oot111/graphics-4k-backup').exists())

    def test_crlf_and_recovery_launcher(self):
        raw = (self.root / 'runtime/frame_rate.c').read_bytes()
        self.put('runtime/frame_rate.c', update.normalized(raw).replace(b'\n', b'\r\n'))
        path = self.root / 'jogar/jogar-ocarina.ps1'
        safe = path.read_bytes().replace(b"TOTK_BIG_CS = '0'", b"TOTK_BIG_CS = '1'")
        self.put('jogar/jogar-ocarina.ps1', safe)
        with patch.object(update, 'build', side_effect=self.built):
            self.assertEqual(update.apply(self.root, self.bundle)['status'], 'updated')
        self.assertIn(b'\r\n', (self.root / 'runtime/frame_rate.c').read_bytes())
        self.assertIn(b"$env:TOTK_BIG_CS = '1'", path.read_bytes())


if __name__ == '__main__':
    unittest.main()
