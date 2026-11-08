$ErrorActionPreference = 'Stop'
try {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $destination = Join-Path $env:OCARINA_BUNDLE_DIR 'unpacked'
    [IO.Compression.ZipFile]::ExtractToDirectory($env:OCARINA_BUNDLE_ZIP, $destination)
    & (Join-Path $destination 'Ocarina-Playback-Fix/fix-ocarina-playback.ps1')
} catch {
    Add-Type -AssemblyName System.Windows.Forms
    [void][Windows.Forms.MessageBox]::Show($_.Exception.Message, '오카리나 연주 수정', 'OK', 'Error')
    exit 1
}
