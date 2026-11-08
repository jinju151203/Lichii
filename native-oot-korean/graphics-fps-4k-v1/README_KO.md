# 오카리나 그래픽 · FPS · 내부 4K 업데이트 v1

게임을 종료하고 `Ocarina_Graphics_FPS_4K_Update.exe`를 실행한 뒤 **기존 OcarinaRecomp 설치 폴더**를 선택하세요.
`ferramentas`, `runtime`, `generated`, `build` 폴더가 들어 있는 상위 폴더입니다.
NUP를 다시 선택하거나 처음부터 재설치할 필요가 없습니다. 저장 파일과 한국어, 컨트롤러 설정은 유지합니다.
설치된 컴파일러로 런타임과 해상도 코드 한 묶음을 다시 빌드하므로 몇 분 걸릴 수 있습니다.

이 파일은 게임 실행 파일을 포함하지 않는 소스 업데이트 도구입니다. 기존 한국어 ko2 포트가 필요합니다.
알 수 없는 소스 수정이 있으면 덮어쓰지 않고 중단합니다.

## 적용 내용

- 최신 리치 소스에서 텍스처 미분·원자 연산의 임시 레지스터 보존과 두 번째 텍스처 버퍼의 gather 처리를 반영합니다.
- 기존 포트의 링크·EXIT·FSEL·가변 gather 수정과 컨트롤러 오카리나 연주용 진동 조회 수정을 유지합니다.
- 셰이더를 읽을 때 EXIT의 두 조건을 모두 검사하여 조건부 종료 뒤의 코드가 잘리지 않도록 합니다.
- 오카리나의 기존 실시간 시간 간격 처리가 있는 빌드에서 호스트의 60Hz 프레임 대기를 해제합니다.
- 메뉴에 240·300 FPS와 **제한 없음**을 추가합니다. 기본 적용값은 제한 없음입니다.
- 내부 3D 해상도 메뉴에 **4K (3840×2160)**를 추가하고 선택합니다. 창 해상도 확대와 별개입니다.
- 실제 NVN 출력 텍스처 크기에 맞춰 게임 내부 렌더링 배율을 계산합니다. 초기 30프레임의 동적 해상도 초기화는 유지합니다.
- 추가 색 보정을 기본값으로 되돌리고, 호스트의 추가 선명화를 끕니다. 기존 검은 화면을 유발했던 Upscaler Test 경로는 안전한 대체 경로를 사용합니다.

## 확인 및 변경

게임 메뉴의 화면 설정에서 내부 3D 해상도와 FPS 제한을 바꿀 수 있습니다.
4K가 무거우면 내부 해상도를 **100 %** 또는 **게임 자동 해상도**로 낮추세요.
프레임을 제한하려면 60·120·144·240·300 등을 선택하세요. 화면 동기화 방식은 mailbox이며, 지원하지 않는 드라이버는 VSync로 돌아갈 수 있습니다.

기존 진단 바로가기로 실행하면 로그에 실제 측정 FPS가 기록됩니다.
렌더러가 실제 3840×2160 색상·깊이 렌더 패스를 관측했을 때만 다음 줄이 출력됩니다.
`resolution: observed 3840x2160 color/depth render pass (internal 4K target)`
이는 해당 크기의 렌더 패스를 확인하는 진단이며 모든 장면·후처리의 4K 품질을 보장하는 표시는 아닙니다.

**실제 게임의 그래픽, 오카리나 연주, 내부 4K 화면과 300FPS 달성은 검증 전입니다.**
FPS 제한 해제는 300FPS 성능 보장을 뜻하지 않습니다. GPU·CPU·드라이버·장면 부하에 따라 달라집니다.
리치의 전체 렌더러나 DLSS를 이식한 빌드는 아닙니다. 고프레임 게임 로직과 4K 메모리 사용은 실험적입니다.

## 백업

변경 전 실행 파일·소스·설정은 `build/oot111/graphics-4k-backup/날짜/`에 보관합니다.
컴파일 또는 실행 파일 연결 검사 실패 시 변경 파일과 기존 실행 파일을 자동 복원합니다.
빌드 로그는 `build/oot111/ocarina-graphics-4k-build.log`입니다.

## 소스와 기준

- Ocarina Recomp: https://github.com/sostenesfreitas/ocarina-recomp/tree/fe7a9399a6daa5a789e7557e5a193db8f3055c2a (0.2.6)
- Lichii: https://github.com/zortos293/Lichii/tree/bf4c42e223d4812d4456d3d8f66d892571d19a13
- 한국어 포트 및 업데이트 소스: https://github.com/jinju151203/Lichii/tree/codex/oot-korean-native/native-oot-korean

압축 파일의 `payload/`에는 변경 소스가, `source/`에는 업데이트 도구와 검증 코드가 있습니다.
원본 프로젝트와 Eglantine/Lichii 코드의 GPL-3.0-or-later 및 THIRD_PARTY_NOTICES를 따릅니다.
게임 데이터, 생성된 게임 C, 저장 파일과 개인 로그는 포함하지 않습니다.

## 소스 검증

이 패치는 기존 `ocarina-recomp-0.2.5-ko2.patch`를 적용한 소스에 대응합니다.
원본 0.2.6 소스에서는 한국어 ko2 패치를 `--exclude=VERSION`으로 먼저 적용하세요.
그 뒤 `git apply --ignore-space-change graphics-fps-4k-v1.patch`로 변경 사항을 적용합니다.
업데이트 EXE는 `tools/oot/make_graphics_4k_update.py --base <변경 전 ko2 소스> --cc <llvm-mingw clang> --windres <windres> --out <EXE>`로 만들 수 있습니다.

검증 결과: Windows x64용 런타임/메뉴/셰이더 컴파일, 실제 셰이더 헤더 2,852개 검사, FPS/4K 정책, 업데이트 성공·중복 적용·원본 보존·세 가지 실패 복구, 한글 카탈로그/실제 ImGui 1080p·4K UI 글꼴, PowerShell 구문 검사 통과.
전체 게임 빌드·실행·그래픽·연주·실제 300FPS·실제 내부 4K 검증은 별도로 필요합니다.

테스트: `python tests/oot_graphics_policy_test.py --cc clang`, `python tests/native_exit_capture_test.py --cxx clang++ --out <임시 폴더>`, `OOT_KO2_BASE=<변경 전 ko2 소스> python tests/oot_graphics_update_test.py`.
