$ErrorActionPreference = 'Stop'
try {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $destination = Join-Path $env:OCARINA_BUNDLE_DIR 'unpacked'
    [IO.Compression.ZipFile]::ExtractToDirectory($env:OCARINA_BUNDLE_ZIP, $destination)
    & (Join-Path $destination 'Ocarina-Graphics-4K/update-graphics-4k.ps1')
} catch {
    Add-Type -AssemblyName System.Windows.Forms
    [void][Windows.Forms.MessageBox]::Show($_.Exception.Message, '오카리나 그래픽 복구 v2', 'OK', 'Error')
    exit 1
}
