# Ocarina Recomp 한국어 Windows 소스와 분석 도구

배포 중인 전체 설치 EXE는 **0.2.1-ko2**입니다. 이 폴더의 **ko3은 개발 소스와 독립 분석 도구**입니다. 기존 설치 EXE가 ko3으로 바뀐 것은 아닙니다. Lichii 실행 파일용 패치가 아니라 별도 네이티브 프로젝트 [sostenesfreitas/ocarina-recomp](https://github.com/sostenesfreitas/ocarina-recomp)의 소스 수정이며, 기준은 `9fb47c63fe9d1021dc9dd9b03210477108e72f54`입니다.

## ko3

- [원본 PR30](https://github.com/sostenesfreitas/ocarina-recomp/pull/30): 진단 환경 변수 읽기를 캐시하고 진단이 꺼진 draw의 진단용 재질 순회를 생략합니다. 렌더링 호출은 유지합니다.
- [원본 PR31](https://github.com/sostenesfreitas/ocarina-recomp/pull/31): NVIDIA의 자동 백그라운드 파이프라인 컴파일을 1개 작업자로 제한합니다. 명시적인 사용자 설정과 다른 GPU 기본값은 유지합니다. 준비 시간이 길어지거나 새 구역에서 컴파일 대기가 늘 수 있습니다.
- `Ocarina_Analysis_Export.exe`: 기존 설치를 선택해 본인 게임 실행 코드와 진단 로그를 개인 분석 ZIP으로 복사합니다. 재설치·재컴파일·그래픽 변경·자동 업로드를 하지 않습니다. RomFS, 세이브, NUP와 키는 수집하지 않습니다. ExeFS 실행 코드가 포함된 결과 ZIP을 GitHub 이슈나 PR에 올리지 마세요.
- 진단에는 GPU·드라이버, 동적 알파 커버리지·색상·선명도·렌더링 설정과 제한된 길이의 실행 로그를 기록합니다. 사진의 검은 캐릭터·밝은 점 증상은 아직 재현하거나 원인을 확정하지 못했습니다.

**실제300FPS·내부4K·모든 깜빡임 해결은 미완성입니다.** 성능 수정의 효과도 이 환경에서 실측하지 않았습니다. 사용자 NUP/ExeFS와 재현 로그가 없어 게임 자체 실행 및 장면 검증은 수행하지 못했습니다. `fps_limit`과 창 크기 설정만 바꿔 달성한 것처럼 표시하지 않습니다.

## ko2에서 유지하는 내용

Lichii `%APPDATA%/eden` 및 포터블 저장 위치 검색·계정 선택, 원본을 변경하지 않는 복사 검증·백업·실패 복구, 한국어 설치/메뉴/공개 글꼴, 진단 실행 바로 가기를 포함합니다. 메시 C0 테이블 충돌 수정 `d637fa727e6b2de860411478fca50a6439d1e4a9`와 일치하는 Windows x64 셰이더 변환기를 재생성했습니다. 이 수정의 실제 게임 장면 개선 범위는 아직 검증하지 못했습니다.

## 소스 적용

각 패치는 아래 기준에 적용하는 **전체 패치**입니다. ko1/ko2 위에 ko3을 연속 적용하지 마세요.

```sh
git clone https://github.com/sostenesfreitas/ocarina-recomp.git
cd ocarina-recomp
git checkout -b korean-0.2.1-ko3 9fb47c63fe9d1021dc9dd9b03210477108e72f54
git apply --check /path/to/ocarina-recomp-ko3.patch
git apply /path/to/ocarina-recomp-ko3.patch
python3 tools/oot/test_perf_policy.py
python3 tools/oot/test_export_analysis.py
python3 tools/oot/test_import_save.py
python3 tools/check_content.py
```

전체 설치 도구를 만들 때 셰이더 변환기는 .NET10 SDK에서 `python3 tools/build_xlate.py --managed-win64 --out build/xlate-managed`로 재생성합니다. 독립 분석 EXE 포장 코드는 `instalador/analysis-bootstrap.ps1`, `instalador/singlefile.c`, `tools/oot/package_singlefile.py --analysis`이며, `jogar/`, `tools/oot/export_analysis.py`, `import_save.py`와 라이선스 고지를 담은 게임 없는 ZIP을 입력합니다. 분석 도구는 기존 설치의 Python을 사용합니다.

게임·키·생성된 게임 C·저장 데이터는 이 소스 패치에 없습니다. 원본 GPL-3.0 및 외부 구성 요소 고지를 유지합니다.

`build_record.json`은 **ko2 설치 EXE** 기록이며, `analysis-export-record.json`은 별도 **ko3 분석 EXE**의 해시·검사·제한 기록입니다. Windows 대상 컴파일 및 PowerShell/Python 연결은 검사했지만 네이티브 Windows GUI와 실제 게임은 실행하지 못했습니다. 기존 `build_xlate_options_test.py`의1개 실패·1개 오류는 ko1에서도 재현되며, `f2i_byte_test.py`의 CPU 평가기는 기본 셰이더의 GLSL 연산80을 지원하지 않아 완료하지 못했습니다. 해당 검사를 통과했다고 기록하지 않았습니다.

이전 ko1/ko2 패치와 ko2 배포 기록은 그대로 보관합니다.
