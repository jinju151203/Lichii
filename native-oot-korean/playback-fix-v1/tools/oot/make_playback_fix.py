#!/usr/bin/env python3
"""Package the small controller-playback fix; only authored source, no game code or tools embedded."""
import argparse
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', type=Path, required=True)
    parser.add_argument('--windres', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    archive = args.out.with_suffix('.zip')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    sources = ['instalador/fix-ocarina-playback.ps1', 'instalador/playback-fix-bootstrap.ps1', 'instalador/singlefile.c',
               'tools/oot/fix_ocarina_playback.py', 'tools/oot/package_singlefile.py', 'tools/oot/make_playback_fix.py',
               'runtime/ov_input.c', 'tests/ounce_vibration_test.py', 'tests/ocarina_playback_patch_test.py',
               'LICENSE', 'LICENSE-MIT']
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        wrapper = (ROOT / 'instalador/fix-ocarina-playback.ps1').read_text(encoding='utf-8-sig')
        bundle.writestr('Ocarina-Playback-Fix/fix-ocarina-playback.ps1',
                        b'\xef\xbb\xbf' + wrapper.replace('\n', '\r\n').encode('utf-8'))
        bundle.write(ROOT / 'tools/oot/fix_ocarina_playback.py', 'Ocarina-Playback-Fix/fix_ocarina_playback.py')
        for source in sources:
            bundle.write(ROOT / source, 'Ocarina-Playback-Fix/source/' + source)
        bundle.writestr('Ocarina-Playback-Fix/README_KO.txt',
                        '오카리나 컨트롤러 연주 종료 수정 v1\n\n'
                        '대상 로그: IsOunceVibrationDeviceMounted 뒤 FATAL: sm: service "hid" is not implemented.\n'
                        '게임을 종료하고 EXE를 실행한 뒤 기존 OcarinaRecomp 설치 폴더를 선택하세요.\n'
                        '기존 소스에 진동 조회 처리를 추가하고 설치된 도구로 실행 파일을 다시 빌드합니다.\n'
                        '재설치하거나 NUP를 다시 선택할 필요가 없습니다.\n'
                        '실행 파일에 새 진동 함수가 연결되었는지 검사한 뒤 완료를 표시합니다.\n'
                        '저장 파일, 언어, 그래픽 설정은 수정하지 않습니다.\n'
                        '백업: build/oot111/playback-backup/. 빌드 실패 시 기존 실행 파일과 소스를 복원합니다.\n'
                        '실제 게임의 연주 동작은 아직 검증 전입니다. 적용 후 컨트롤러로 연주해 보세요.\n'
                        '실패 로그: build/oot111/ocarina-playback-build.log\n'
                        'source/에 대응 소스와 라이선스가 있습니다.\n')
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip():
            raise ValueError('Playback fix ZIP checksum failed')
    subprocess.run([sys.executable, str(ROOT / 'tools/oot/package_singlefile.py'), str(archive),
                    '--cc', str(args.cc.absolute()), '--windres', str(args.windres.absolute()),
                    '--out', str(args.out.resolve()), '--playback-fix'], check=True)


if __name__ == '__main__':
    main()
