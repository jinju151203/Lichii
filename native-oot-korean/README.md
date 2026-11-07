# Ocarina Recomp 한국어·연주 안정성 수정 0.2.5-ko2

최신 정식판 v0.2.5 이후의 **원본 main `ada56edf88765399eb4b3d58cc6b7a11162ed58e`**를 기준으로 합니다.
원본: https://github.com/sostenesfreitas/ocarina-recomp
2026-11-08 한국 시간에 확인한 기준입니다.

## 적용 범위

게임의 그래픽·셰이더 변환·프레임·해상도 처리 코드는 위 원본과 같습니다.
한국어 UI/언어 설정, 저장 데이터 보호, 미사용 마이크 API 처리와 충돌 로그 수집을 덧붙였습니다.
이전 수정판의 별도 Sqrt 실험 코드와 오카리나 해상도 실험 UI는 정리했습니다.
기존 그래픽 설정과 이미 고쳐진 링크 설정은 유지합니다.

원본에 새로 추가된 내용도 포함합니다.

- Ampere SEL/FSEL의 uniform 입력, 마지막 RET.REL, 레지스터 사용량 처리 수정.
- RGB9E5와 R11G11B10F 텍스처의 색상 포맷을 혼동해 검은 화면이 생기는 경로 수정.
- GPU 메모리 부족 시 확대용 임시 이미지 생성 실패로 바로 종료하던 경로의 처리.
- VMA 메모리 블록 기본 크기를 줄이는 원본 변경.

이 변경이 사용자의 픽셀 느낌이나 오프닝 줄무늬를 모두 해결했는지는 아직 실제 장면에서 확인하지 못했습니다.
선명도·색상은 원본 설정을 따릅니다.

바탕 화면 **Ocarina Recomp - Upscaler Test**는 원본의 TOTK_BIG_CS=0 옵션으로 게임 업스케일러를 사용합니다.
기본 실행의 단순 확대보다 선명할 수 있지만 GPU 부담과 컴파일 시간이 달라집니다.
이 모드는 시험용이며 사용자 GPU에서 검증하지 못했습니다. 기본 Ocarina Recomp 바로 가기는 원본 기본 동작을 유지합니다.
이 선택은 설정 파일에 저장하지 않으며, 새로 추가한 렌더링 코드가 아닌 원본에 있는 실행 옵션입니다.

## 오카리나 연주 수정

원본에는 미사용 마이크의 Purge/Statistics 등 일부 API 우회가 이미 있었습니다.
이 수정은 빠져 있던 public 장치 목록, Open/Start/Stop/Close/Read, 채워진 프레임 수, Format, Gain 등의 처리를 보완합니다.
마이크 입력을 열 수 없으면 실패를 반환하고 닫힌 상태로 유지하며, 초기화되지 않은 스트림 내부 포인터를 읽지 않습니다.
통계는 x8 결과에 정확히 24바이트만 쓰고, 형식/게인은 AAPCS64 규칙대로 반환합니다.
기존 detail 목록 함수도 함께 등록해 총 17개 이름을 처리합니다.

실제 런타임의 이름 조회/링커 테이블을 사용해 닫힌 스트림·잘못된 객체 주소, 결과 레지스터,
24바이트 결과 주변 값 보존, 3,000회 반복 호출을 검사했습니다.
**게임에서 연주를 직접 재현한 검증은 아니므로 사용자 환경의 연주 종료가 완전히 해결됐다고 확정하지 않습니다.**

## 기존 설치에 업데이트

1. 게임과 Lichii를 종료하고 Ocarina_Korean_Setup.exe를 실행합니다.
2. **기존 OcarinaRecomp 설치 폴더**를 선택합니다. 폴더를 먼저 삭제하지 마세요.
3. 기존 exefs/romfs를 재사용해 실행 파일을 빌드합니다. 세이브와 기존 설정을 유지합니다.
4. 이번 원본 셰이더 변경을 반영하기 위해 업데이트 후 셰이더 미리 준비를 다시 진행합니다.
   이전 완료 표시만 갱신하며 기존 셰이더 캐시 파일은 보존합니다. 준비 시간이 걸릴 수 있습니다.

새 설치는 본인이 가진 Switch 2판 1.1.1 NUP 또는 exefs/romfs 폴더가 필요합니다.
이 EXE는 설치 도구입니다. 게임 실행 코드나 리소스·키는 포함하지 않으며, 본인 PC에서 build/oot111/ocarina.exe를 만듭니다.

## 언어와 저장

게임 언어는 F1 → 게임에서, PC 설정 메뉴 언어는 F1 → 메뉴에서 변경합니다.
한국어 대사와 게임 메뉴는 본인 게임 파일에 있는 한국어 리소스를 사용합니다.
설치는 언어 키만 한국어로 적용하고 변경 전 설정을 totk.ini.before-korean.bak에 백업합니다.
바탕 화면 Ocarina Recomp - Lichii Save는 계정 선택·복사 검증·기존 저장 백업·실패 복구를 유지합니다.

## 문제가 남을 때

비정상 종료 뒤 표시되는 oot-diagnostics-날짜.zip을 이 채팅에 첨부하고,
악기를 꺼낼 때/첫 음/특정 곡 중 어느 때인지 함께 알려주세요. 오프닝 줄무늬가 계속되면 그 장면 사진도 도움이 됩니다.
진단은 GPU·드라이버, 설정과 최근 로그만 수집하며 게임·세이브·키는 포함하지 않습니다. 자동 전송하지 않습니다.
설치 폴더 diagnostics에서도 찾을 수 있고, 바탕 화면 Ocarina Recomp - Diagnostics로 재현할 수도 있습니다.

본인 실행 코드를 추가 분석 ZIP으로 복사하는 Export Analysis 도구는 별도입니다.
그 ZIP에는 본인 게임의 ExeFS 모듈이 들어가므로 GitHub 이슈나 PR에 올리지 마세요.

## 검증과 라이선스

사용자 NUP/ExeFS/재현 로그가 이 환경에 없어 최종 게임 빌드·연주·오프닝·화질·FPS 실측은 수행하지 못했습니다.
원본 프레임/해상도 동작을 따르며 300FPS나 내부4K를 강제하는 추가 패치는 없습니다.
검사와 파일 해시는 공개 소스 폴더의 build_record-0.2.5-ko2.json에 기록합니다.
원본 GPL-3.0, 외부 도구 고지, OFL 메뉴 글꼴 및 seedds의 MIT 고지를 유지합니다.
수정 소스는 설치판 projeto에 포함하며, 다음 위치에도 보관합니다.
https://github.com/jinju151203/Lichii/tree/codex/oot-korean-native/native-oot-korean

## 전체 소스 패치 적용

현재 배포 기록은 `build_record-0.2.5-ko2.json`입니다. 이전 패치·기록은 이전 버전 자료로 보관합니다.
`ocarina-recomp-0.2.5-ko2.patch`는 아래 원본 커밋에 적용하는 전체 수정이므로 이전 ko 패치와 연속 적용하지 마세요.

```sh
git clone https://github.com/sostenesfreitas/ocarina-recomp.git
cd ocarina-recomp
git checkout -b korean-0.2.5-ko2 ada56edf88765399eb4b3d58cc6b7a11162ed58e
git apply --check /path/to/ocarina-recomp-0.2.5-ko2.patch
git apply /path/to/ocarina-recomp-0.2.5-ko2.patch
python3 tests/audio_input_compat_test.py --cc clang
python3 tools/check_content.py
```
