#!/usr/bin/env python3
"""Exercise the actual HID mount handlers on authored controller handles, without a game or SDL."""
import argparse
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', default='clang')
    args = parser.parse_args()
    source = (ROOT / 'runtime/ov_input.c').read_text()
    assert 'HOST_OVERRIDE("_ZN2nn3hid29IsOunceVibrationDeviceMountedERKNS0_21VibrationDeviceHandleE", ov_vib_mounted_ounce);' in source
    assert 'HOST_OVERRIDE("_ZN2nn3hid6detail29IsOunceVibrationDeviceMountedEPbRKNS0_21VibrationDeviceHandleE", ov_vib_mounted);' in source
    code = r'''
#include <assert.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#include "host.h"
// Do not retain unrelated handlers in this standalone executable; the code under test is included verbatim below.
#undef HOST_OVERRIDE
#define HOST_OVERRIDE(name, fn)
#include "ov_input.c"
static int handheld;
int ov_handheld(void) { return handheld; }
void rt_log(const char *format, ...) { (void)format; }
void rt_fatal(const char *format, ...) { (void)format; abort(); }

static void query(uint32_t handle, int expected) {
    Cpu c; memset(&c, 0xa5, sizeof c);
    c.x[0] = (uintptr_t)&handle;
    Cpu before = c;
    ov_vib_mounted_ounce(&c);
    assert(c.x[0] == (uint64_t)expected);
    before.x[0] = c.x[0];
    assert(!memcmp(&before, &c, sizeof c));
    uint8_t guarded[9]; memset(guarded, 0xa5, sizeof guarded);
    c = before; c.x[0] = (uintptr_t)(guarded + 4); c.x[1] = (uintptr_t)&handle;
    before = c;
    ov_vib_mounted(&c);
    assert(c.x[0] == 0); before.x[0] = 0;
    assert(!memcmp(&before, &c, sizeof c));
    for (unsigned i=0;i<sizeof guarded;i++) assert(guarded[i] == (i==4 ? expected : 0xa5));
}
int main(void) {
    for (handheld=0;handheld<2;handheld++) {
        for (unsigned style=0;style<9;style++) {
            for (unsigned player=0;player<=32;player+=8) {
                for (unsigned device=0;device<4;device++) {
                    uint32_t handle=style | player<<8 | device<<16;
                    int expected=style==(handheld?4:3) && player==(handheld?32:0) && device<2;
                    query(handle,expected);
                }
            }
        }
    }
    handheld=0;
    for (int i=0;i<1000;i++) { query(3,1);query(0x10003,1);query(0x20003,0); }
    puts("PASS: real Ounce public bool / detail Result+one-byte output; docked/handheld, both motors, invalid handles, register guards, repeated playback queries");
}
'''
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        test = folder / 'test.c'
        test.write_text(code)
        exe = folder / 'test'
        subprocess.run([args.cc, '-std=gnu11', '-O2', '-Wall', '-Wextra', '-Werror',
                        '-Wno-unused-function', '-Wno-unused-variable', '-ffunction-sections', '-fdata-sections',
                        '-I', str(ROOT / 'runtime'), str(test), '-Wl,--gc-sections', '-lm', '-o', str(exe)], check=True)
        subprocess.run([str(exe)], check=True)


if __name__ == '__main__':
    main()
