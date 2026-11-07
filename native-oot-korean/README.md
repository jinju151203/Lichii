# Ocarina Recomp 한국어 Windows 설치판 ko2 소스

현재 수정판은 **0.2.1-ko2**입니다. Lichii 실행 파일에 직접 적용하는 패치가 아니라, 별도 네이티브 프로젝트인 sostenesfreitas/ocarina-recomp v0.2.1의 수정 소스입니다. 기준 커밋은 `9fb47c63fe9d1021dc9dd9b03210477108e72f54`입니다.

이번 변경:

- Lichii의 실제 `%APPDATA%/eden` 저장 위치와 구형·신형 계정 구조 검색, 포터블 폴더 수동 선택, 여러 계정 선택.
- 원본을 변경하지 않는 SHA-256 복사 검증. 기존 포트 저장과 대기 중인 `save-tx`를 함께 백업하고, 교체 실패 시 복구.
- 원본의 메시 C0 테이블 충돌 수정 `d637fa727e6b2de860411478fca50a6439d1e4a9` 반영. 해당 작성자의 변경은 원래 라이선스와 고지를 유지합니다.
- 동일한 C0 배치로 재빌드한 Windows x64 셰이더 변환기를 설치판에 포함. .NET 구성 요소도 자체 포함하며 게임은 기존 C 정적 재컴파일 경로를 유지합니다.
- 한국어 설치·메뉴·공개 글꼴 및 진단 실행 바로 가기. 내부 장면 크기를 측정하지 못한 경우 성능 표시에 추정 해상도를 표시하지 않음.

**실제300FPS·내부4K·모든 깜빡임 해결은 아직 완성하지 못했습니다.** NUP/ExeFS와 재현 로그가 이 작업 환경에 없어 게임 자체 실행 및 장면 검증은 수행하지 못했습니다. 이를 달성한 것처럼 설정값이나 측정 결과를 넣지 않았습니다.

적용:

```sh
git clone https://github.com/sostenesfreitas/ocarina-recomp.git
cd ocarina-recomp
git checkout -b korean-0.2.1-ko2 9fb47c63fe9d1021dc9dd9b03210477108e72f54
git apply --check /path/to/ocarina-recomp-ko2.patch
git apply /path/to/ocarina-recomp-ko2.patch
python3 tools/oot/test_import_save.py
python3 tests/c0_layout_test.py --cc clang
python3 tools/check_content.py
```

셰이더 변환기는 .NET10 SDK에서 `python3 tools/build_xlate.py --managed-win64 --out build/xlate-managed`로 재생성합니다. 단일 EXE의 포장 코드는 `instalador/singlefile.c`, `instalador/bootstrap.ps1`, `tools/oot/package_singlefile.py`입니다. 소스 패치에는 게임·키·생성된 게임 C·저장 데이터가 없습니다. 원본 GPL-3.0 및 외부 구성 요소 고지를 유지합니다.

`build_record.json`은 배포 설치 EXE의 해시, 통과한 검사 및 남은 검증을 기록합니다. 추가로 실행한 기존 `build_xlate_options_test.py`는 ko1에서도 재현되는1개 실패·1개 오류가 있으며, `f2i_byte_test.py`의 CPU 평가기는 기본 셰이더의 GLSL 연산80을 해석하지 못해 검사를 완료하지 못했습니다. 해당 검사를 통과했다고 기록하지 않았습니다.

이전 ko1 패치는 같은 폴더의 `ocarina-recomp-ko1.patch`에 남겨 두었습니다.
