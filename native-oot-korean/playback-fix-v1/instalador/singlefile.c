// Single-file Korean setup: unpack the bundled tools/source, then run the native-build installer.
// The game is built from the player's own NUP on their PC. No game executable is embedded here.
#ifndef UNICODE
#define UNICODE 1
#endif
#ifndef _UNICODE
#define _UNICODE 1
#endif
#include <windows.h>
#include <objbase.h>
#include <stdio.h>
#include <stdlib.h>
#include <wchar.h>

#define PATH_CAP 32768

static int write_resource(int id, const wchar_t *file) {
    HRSRC resource = FindResourceW(NULL, MAKEINTRESOURCEW(id), RT_RCDATA);
    if (!resource) return 0;
    DWORD size = SizeofResource(NULL, resource), written = 0;
    const void *data = LockResource(LoadResource(NULL, resource));
    if (!data || !size) return 0;
    HANDLE output = CreateFileW(file, GENERIC_WRITE, 0, NULL, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, NULL);
    if (output == INVALID_HANDLE_VALUE) return 0;
    int ok = WriteFile(output, data, size, &written, NULL) && written == size;
    CloseHandle(output);
    return ok;
}

// Only called on the unique temporary folder this process created. Never traverse reparse points.
static void clean_folder(const wchar_t *folder) {
    wchar_t *pattern = calloc(PATH_CAP, sizeof *pattern);
    wchar_t *child = calloc(PATH_CAP, sizeof *child);
    if (!pattern || !child) goto done;
    if (swprintf(pattern, PATH_CAP, L"%ls\\*", folder) < 0) goto done;
    WIN32_FIND_DATAW entry;
    HANDLE search = FindFirstFileW(pattern, &entry);
    if (search != INVALID_HANDLE_VALUE) {
        do {
            if (!wcscmp(entry.cFileName, L".") || !wcscmp(entry.cFileName, L"..")) continue;
            if (swprintf(child, PATH_CAP, L"%ls\\%ls", folder, entry.cFileName) < 0) continue;
            if (entry.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
                if (entry.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) RemoveDirectoryW(child);
                else clean_folder(child);
            } else DeleteFileW(child);
        } while (FindNextFileW(search, &entry));
        FindClose(search);
    }
    RemoveDirectoryW(folder);
done:
    free(pattern);
    free(child);
}

int WINAPI wWinMain(HINSTANCE self, HINSTANCE previous, PWSTR line, int show) {
    (void)self; (void)previous; (void)line; (void)show;
    wchar_t *temp = calloc(PATH_CAP, sizeof *temp);
    wchar_t *folder = calloc(PATH_CAP, sizeof *folder);
    wchar_t *archive = calloc(PATH_CAP, sizeof *archive);
    wchar_t *script = calloc(PATH_CAP, sizeof *script);
    wchar_t *command = calloc(2 * PATH_CAP, sizeof *command);
    wchar_t system[MAX_PATH], guid_text[40];
    GUID guid;
    int result = 2, made_folder = 0;
    if (!temp || !folder || !archive || !script || !command) goto failure;
    DWORD size = GetTempPathW(PATH_CAP, temp);
    if (!size || size >= PATH_CAP || FAILED(CoCreateGuid(&guid)) || !StringFromGUID2(&guid, guid_text, 40)) goto failure;
    if (swprintf(folder, PATH_CAP, L"%lsOcarinaKR-%ls", temp, guid_text) < 0 || !CreateDirectoryW(folder, NULL)) goto failure;
    made_folder = 1;
    if (swprintf(archive, PATH_CAP, L"%ls\\payload.zip", folder) < 0 ||
        swprintf(script, PATH_CAP, L"%ls\\prepare.ps1", folder) < 0 ||
        !write_resource(101, archive) || !write_resource(102, script)) goto failure;
    SetEnvironmentVariableW(L"OCARINA_BUNDLE_ZIP", archive);
    SetEnvironmentVariableW(L"OCARINA_BUNDLE_DIR", folder);
    if (!GetSystemDirectoryW(system, MAX_PATH)) goto failure;
    if (swprintf(command, 2 * PATH_CAP,
        L"\"%ls\\WindowsPowerShell\\v1.0\\powershell.exe\" -NoProfile -Sta -WindowStyle Hidden -ExecutionPolicy Bypass -File \"%ls\"",
        system, script) < 0) goto failure;
    STARTUPINFOW startup = {.cb = sizeof startup};
    PROCESS_INFORMATION process;
    if (!CreateProcessW(NULL, command, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, folder, &startup, &process)) goto failure;
    CloseHandle(process.hThread);
    WaitForSingleObject(process.hProcess, INFINITE);
    DWORD code = 1;
    GetExitCodeProcess(process.hProcess, &code);
    CloseHandle(process.hProcess);
    result = (int)code;
    goto done;
failure:
#if defined(PLAYBACK_FIX)
    MessageBoxW(NULL, L"오카리나 연주 수정 도구를 준비하지 못했습니다. 임시 폴더의 여유 공간을 확인하고 다시 실행하세요.",
                L"오카리나 연주 수정", MB_OK | MB_ICONERROR);
#elif defined(DISPLAY_RECOVERY)
    MessageBoxW(NULL, L"화면 복구 도구를 준비하지 못했습니다. 임시 폴더의 여유 공간을 확인하고 다시 실행하세요.",
                L"Ocarina 화면 복구", MB_OK | MB_ICONERROR);
#elif defined(ANALYSIS_EXPORTER)
    MessageBoxW(NULL, L"분석 도구를 준비하지 못했습니다. 임시 폴더의 여유 공간을 확인하고 다시 실행하세요.\n\nWindows 10/11 64비트와 Windows PowerShell이 필요합니다.",
                L"Ocarina 분석 자료 내보내기", MB_OK | MB_ICONERROR);
#else
    MessageBoxW(NULL, L"설치 파일을 준비하지 못했습니다. 임시 폴더의 여유 공간을 확인하고 다시 실행하세요.\n\nWindows 10/11 64비트와 Windows PowerShell이 필요합니다.",
                L"Ocarina Recomp 한국어 설치", MB_OK | MB_ICONERROR);
#endif
done:
    if (made_folder) clean_folder(folder);
    free(temp); free(folder); free(archive); free(script); free(command);
    return result;
}
