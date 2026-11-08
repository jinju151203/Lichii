#!/usr/bin/env python3
"""Build an x64 Windows setup or analysis-helper EXE embedding a prepared, game-free ZIP."""
import argparse
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('zip', type=Path)
    parser.add_argument('--cc', type=Path, required=True, help='x86_64-w64-mingw32-clang[.exe]')
    parser.add_argument('--windres', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--analysis', action='store_true', help='package the standalone private-analysis helper instead of setup')
    parser.add_argument('--display-recovery', action='store_true', help='package the ko2 upscaler-test recovery helper')
    parser.add_argument('--playback-fix', action='store_true', help='package the controller-playback HID fix')
    args = parser.parse_args()
    if sum((args.analysis, args.display_recovery, args.playback_fix)) > 1:
        parser.error('helper modes are mutually exclusive')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        script = folder / 'bootstrap.ps1'
        bootstrap = 'display-recovery-bootstrap.ps1' if args.display_recovery else 'analysis-bootstrap.ps1' if args.analysis else 'bootstrap.ps1'
        if args.playback_fix:
            bootstrap = 'playback-fix-bootstrap.ps1'
        source = (ROOT / 'instalador' / bootstrap).read_text(encoding='utf-8-sig')
        script.write_bytes(b'\xef\xbb\xbf' + source.replace('\n', '\r\n').encode('utf-8'))
        manifest = folder / 'setup.manifest'
        manifest.write_text('''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
<assemblyIdentity type="win32" name="OcarinaRecomp.KoreanSetup" version="0.2.5.2" processorArchitecture="amd64"/>
<trustInfo xmlns="urn:schemas-microsoft-com:asm.v3"><security><requestedPrivileges><requestedExecutionLevel level="asInvoker" uiAccess="false"/></requestedPrivileges></security></trustInfo>
<application xmlns="urn:schemas-microsoft-com:asm.v3"><windowsSettings><longPathAware xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">true</longPathAware></windowsSettings></application>
</assembly>'''.replace('OcarinaRecomp.KoreanSetup', 'OcarinaRecomp.AnalysisExport' if args.analysis else 'OcarinaRecomp.KoreanSetup'))
        rc = folder / 'setup.rc'
        quoted = lambda p: '"' + str(p.resolve()).replace('\\', '/') + '"'
        rc.write_text('101 RCDATA ' + quoted(args.zip) + '\n102 RCDATA ' + quoted(script) +
                      '\n1 24 ' + quoted(manifest) + '''
1 VERSIONINFO
 FILEVERSION 0,2,5,2
 PRODUCTVERSION 0,2,5,2
 FILEOS 0x40004
 FILETYPE 1
BEGIN
 BLOCK "StringFileInfo"
 BEGIN
  BLOCK "040904b0"
  BEGIN
   VALUE "FileDescription", "Ocarina Recomp Korean Native Build Setup\\0"
   VALUE "FileVersion", "0.2.5-ko2\\0"
   VALUE "ProductName", "Ocarina Recomp Korean Setup\\0"
   VALUE "OriginalFilename", "Ocarina_Korean_Setup.exe\\0"
  END
 END
 BLOCK "VarFileInfo"
 BEGIN
  VALUE "Translation", 0x409, 1200
 END
END
''')
        if args.analysis:
            rc.write_text(rc.read_text().replace('Ocarina Recomp Korean Native Build Setup', 'Ocarina Recomp Private Analysis Export')
                          .replace('Ocarina Recomp Korean Setup', 'Ocarina Recomp Analysis Export')
                          .replace('Ocarina_Korean_Setup.exe', 'Ocarina_Analysis_Export.exe'))
        if args.display_recovery:
            rc.write_text(rc.read_text().replace('Ocarina Recomp Korean Native Build Setup', 'Ocarina Recomp Display Recovery')
                          .replace('Ocarina Recomp Korean Setup', 'Ocarina Recomp Display Recovery')
                          .replace('Ocarina_Korean_Setup.exe', 'Ocarina_Display_Recovery.exe'))
        if args.playback_fix:
            rc.write_text(rc.read_text().replace('Ocarina Recomp Korean Native Build Setup', 'Ocarina Recomp Ocarina Playback Fix')
                          .replace('Ocarina Recomp Korean Setup', 'Ocarina Recomp Controller Playback Fix')
                          .replace('Ocarina_Korean_Setup.exe', 'Ocarina_Playback_Fix.exe'))
        resource = folder / 'setup.res'
        subprocess.run([str(args.windres), '-i', str(rc), '-o', str(resource), '-O', 'coff'], check=True)
        subprocess.run([str(args.cc), '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-municode', '-mwindows',
                        str(ROOT / 'instalador/singlefile.c'), str(resource), '-lole32', '-static', '-s',
                        *(['-DANALYSIS_EXPORTER=1'] if args.analysis else []),
                        *(['-DDISPLAY_RECOVERY=1'] if args.display_recovery else []),
                        *(['-DPLAYBACK_FIX=1'] if args.playback_fix else []), '-o', str(args.out)], check=True)
    print(f'{args.out}: {args.out.stat().st_size:,} bytes')


if __name__ == '__main__':
    main()
