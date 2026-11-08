"""Exercise the real frame limiter, output-size policy and authored resolution hook without game files."""
import argparse
import importlib.util
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cc', default='clang')
    args = ap.parse_args()
    spec = importlib.util.spec_from_file_location('pg', ROOT / 'tools/oot/patch_generated.py')
    pg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pg)
    source = r'''
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "frame_rate.c"
const int rt_oot_clock = CLOCK;
const int rt_game_version = 0;
static const char *setting = "300", *resolution = "4k";
static unsigned revision;
const char *cfg_get(const char *key) {
    if (!strcmp(key,"TOTK_FPS_LIMIT")) return setting;
    if (!strcmp(key,"TOTK_OOT_RESOLUTION")) return resolution;
    return NULL;
}
unsigned cfg_version(void) { return revision; }
void rt_log(const char *fmt, ...) { (void)fmt; }
int rt_patch_set(const char *name) { (void)name; return -1; }
int rt_patch_enabled(int set) { (void)set; return 0; }
void rt_patch_disable(int set) { (void)set; }
void rt_patch_switch(int set,int on) { (void)set;(void)on; }
void *rt_patch_page(void) { return NULL; }
double gfx_window_refresh_hz(void) { return 144; }
'''
    source += pg.FIXED_RES
    source += r'''
static void cap(const char *value, uint64_t expected) {
    setting = value; revision++;
    assert(frame_step_cap_ns() == expected);
}
int main(int argc, char **argv) {
    const int timed = CLOCK && argc == 1;
    if (argc > 1) assert(!strcmp(argv[1],"disabled"));
    frame_step_init();
    assert(frame_step_realtime() == timed);
    cap("300",3333333); cap("240",4166667); cap("display",6944444);
    cap("unlimited",timed ? 0 : 16666667);
    assert(frame_step_limit_hz() == (timed ? 0 : 60));
    cap("bad",16666667); cap("30",33333333); cap("360",2777778);
    assert(oot_internal_4k_scale() == 0);
    if (CLOCK) {
        oot_note_output(1280,720); assert(oot_internal_4k_scale() == 3);
        oot_note_output(1920,1080); assert(oot_internal_4k_scale() == 2);
        oot_note_output(2560,1440); assert(oot_internal_4k_scale() == 1.5f);
        for (oot_dynres_runs=0;oot_dynres_runs<30;oot_dynres_runs++) assert(!oot_fixed_res());
        assert(oot_fixed_res());
        union { uint32_t u; float f; } scale = {oot_res_bits}; assert(scale.f == 1.5f);
        oot_note_output(3840,2160); assert(oot_fixed_res()); scale.u=oot_res_bits; assert(scale.f==1);
        oot_note_output(1280,800); assert(!oot_fixed_res());
        oot_note_output(1920,1080); assert(oot_fixed_res());
        resolution="100";revision++;assert(oot_fixed_res()); scale.u=oot_res_bits;assert(scale.f==1);
        resolution="auto";revision++;assert(!oot_fixed_res());
        resolution="garbage";revision++;assert(!oot_fixed_res());
    }
    puts("PASS: real FPS limiter, clock guard, internal 4K output scaling, 30-frame initialization and live modes");
}
'''
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        (folder / 'layout.h').write_text('#define MOD_MAIN_BASE 0x7000000000ull\n')
        (folder / 'policy.c').write_text(source)
        for clock in (0, 1):
            exe = folder / f'policy-{clock}'
            subprocess.run([args.cc, '-std=gnu11', '-O2', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                            '-ffunction-sections', '-fdata-sections', f'-DCLOCK={clock}',
                            '-I', str(folder), '-I', str(ROOT / 'runtime'), str(folder / 'policy.c'),
                            str(ROOT / 'runtime/oot_render_policy.c'), '-Wl,--gc-sections', '-lm', '-o', str(exe)], check=True)
            subprocess.run([str(exe)], check=True)
            if clock:
                import os
                subprocess.run([str(exe), 'disabled'], env=dict(os.environ, OOT_DYN_DT='0'), check=True)
    original = '/* fixture */\n' + pg.FIXED_RES_V1 + 'void fixture(void) {}\n'
    updated = pg.upgrade_fixed_resolution(original)
    assert pg.upgrade_fixed_resolution(updated) == updated
    assert updated.startswith('/* fixture */') and updated.endswith('void fixture(void) {}\n')
    try:
        pg.upgrade_fixed_resolution('unknown hook')
        raise AssertionError('unknown generated source accepted')
    except ValueError:
        pass
    print('PASS: authored-block-only upgrade, idempotence, unknown-source rejection')


if __name__ == '__main__':
    main()
