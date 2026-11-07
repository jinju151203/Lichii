# Ocarina Recomp 한국어 Windows 설치판 소스

이 폴더는 별도 네이티브 프로젝트인 sostenesfreitas/ocarina-recomp v0.2.1에 적용하는 패치입니다. Lichii 실행 파일에 패치를 적용하지 않습니다.
기준 커밋: `9fb47c63fe9d1021dc9dd9b03210477108e72f54`.
참고: https://github.com/seedds/nxnative/tree/main/dm/games/0400486024DEC000

한국어 게임 언어 선택, 완전한 F1 한국어 메뉴, 내장 OFL 글꼴, 기존 설정 백업, 한국어 설치 화면, 단일 Windows 설치 EXE의 소스를 포함합니다. 사용자가 가진 NUP1.1.1로 게임 EXE를 PC에서 생성합니다. 게임 데이터·생성된 게임 코드는 없습니다. 실제300FPS·내부4K·깜빡임 완전 해결은 검증하지 않았습니다.

적용 예시:

```sh
git clone https://github.com/sostenesfreitas/ocarina-recomp.git
cd ocarina-recomp
git checkout -b korean-0.2.1 9fb47c63fe9d1021dc9dd9b03210477108e72f54
git apply --check /path/to/ocarina-recomp-ko1.patch
git apply /path/to/ocarina-recomp-ko1.patch
python3 tools/oot/test_korean.py
python3 tools/check_content.py
```

자세한 사용법과 제한은 패치에 추가된 README_KO.md에 있습니다. 원본 GPL-3.0 및 외부 구성 요소의 고지를 유지합니다. 글꼴 라이선스와 재생성 도구도 패치에 포함했습니다.

`build_record.json`은 배포 설치 EXE의 해시와 확인 범위입니다. 이 EXE는 완성된 게임이 아니라 사용자의 NUP에서 네이티브 게임 실행 파일을 만드는 설치 프로그램입니다. Windows 게임 실행 검증은 아직 수행하지 못했습니다.
