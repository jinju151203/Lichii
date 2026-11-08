# Targeted controller-playback fix. Uses the installed Python/compiler and existing owned-game build.
param([string]$InstallRoot, [switch]$SemJanela)
$ErrorActionPreference = 'Stop'
function Quote-PlaybackArgument([string]$Value) {
    $quoted = [regex]::Replace($Value, '(\\*)"', '$1$1\"')
    $quoted = [regex]::Replace($quoted, '(\\+)$', '$1$1')
    return '"' + $quoted + '"'
}
if ($MyInvocation.InvocationName -eq '.') { return }
$progress = $null
$process = $null
try {
    if (-not $SemJanela) {
        Add-Type -AssemblyName System.Windows.Forms, System.Drawing
        [Windows.Forms.Application]::EnableVisualStyles()
        if (-not $InstallRoot) {
            $dialog = New-Object Windows.Forms.FolderBrowserDialog
            $dialog.Description = '기존 OcarinaRecomp 설치 폴더를 선택하세요. 오카리나 연주 시 컨트롤러 진동 조회 오류만 수정합니다.'
            if (Test-Path -LiteralPath 'C:\OcarinaRecomp') { $dialog.SelectedPath = 'C:\OcarinaRecomp' }
            if ($dialog.ShowDialog() -ne 'OK') { $dialog.Dispose(); exit 0 }
            $InstallRoot = $dialog.SelectedPath
            $dialog.Dispose()
        }
    }
    if (-not $InstallRoot) { throw '기존 게임 설치 폴더가 필요합니다.' }
    $root = [IO.Path]::GetFullPath($InstallRoot)
    $game = [IO.Path]::GetFullPath((Join-Path $root 'build/oot111/ocarina.exe'))
    if (Get-Process ocarina -ErrorAction SilentlyContinue | Where-Object { $_.Path -and [string]::Equals($_.Path, $game, [StringComparison]::OrdinalIgnoreCase) }) {
        throw '게임을 종료한 뒤 다시 실행하세요.'
    }
    $python = Join-Path $root 'ferramentas/python/python.exe'
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw '설치된 도구를 찾지 못했습니다. ferramentas 폴더가 있는 기존 OcarinaRecomp 폴더를 선택하세요.' }
    $helper = Join-Path $PSScriptRoot 'fix_ocarina_playback.py'
    if (-not $SemJanela) {
        $progress = New-Object Windows.Forms.Form
        $progress.Text = '오카리나 연주 수정 중'
        $progress.ClientSize = New-Object Drawing.Size(610, 155)
        $progress.StartPosition = 'CenterScreen'
        $progress.ControlBox = $false
        $progress.Font = New-Object Drawing.Font('Malgun Gothic', 10)
        $status = New-Object Windows.Forms.Label
        $status.SetBounds(18, 18, 575, 120)
        $status.Text = "기존 실행 파일을 백업하고 컨트롤러 진동 조회 처리를 추가합니다.`n설치된 도구로 로컬 실행 파일을 다시 연결합니다. 잠시 기다려 주세요.`n`n저장 파일과 그래픽 설정은 변경하지 않습니다."
        $progress.Controls.Add($status)
        $progress.Show(); $progress.Refresh()
    }
    $psi = New-Object Diagnostics.ProcessStartInfo
    $psi.FileName = $python
    $psi.Arguments = (@($helper, '--root', $root) | ForEach-Object { Quote-PlaybackArgument ([string]$_) }) -join ' '
    $psi.WorkingDirectory = $root
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.StandardOutputEncoding = New-Object Text.UTF8Encoding($false)
    $psi.StandardErrorEncoding = New-Object Text.UTF8Encoding($false)
    $psi.EnvironmentVariables['PYTHONUTF8'] = '1'
    $process = New-Object Diagnostics.Process
    $process.StartInfo = $psi
    [void]$process.Start()
    $stdout = $process.StandardOutput.ReadToEndAsync()
    $stderr = $process.StandardError.ReadToEndAsync()
    while (-not $process.HasExited) {
        if (-not $SemJanela) { [Windows.Forms.Application]::DoEvents() }
        [Threading.Thread]::Sleep(50)
    }
    $process.WaitForExit()
    $text = $stdout.GetAwaiter().GetResult()
    $errorText = $stderr.GetAwaiter().GetResult()
    if (-not $text.Trim()) { throw $errorText }
    $result = $text | ConvertFrom-Json
    if ($process.ExitCode -ne 0) { throw $result.error }
    if ($progress) { $progress.Close() }
    Write-Output $text
    if (-not $SemJanela) {
        [void][Windows.Forms.MessageBox]::Show("$($result.message)`n`n기존 게임 바로가기로 실행해 컨트롤러로 오카리나를 연주해 보세요.`n`n실제 게임에서의 연주 확인은 아직 필요합니다.", '오카리나 연주 수정', 'OK', 'Information')
    }
} catch {
    if ($SemJanela) { throw }
    [void][Windows.Forms.MessageBox]::Show($_.Exception.Message, '오카리나 연주 수정', 'OK', 'Error')
    exit 1
} finally {
    if ($process) { $process.Dispose() }
    if ($progress) { $progress.Dispose() }
}
