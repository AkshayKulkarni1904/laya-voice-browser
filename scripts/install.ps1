# Windows Setup Script for LayaBrowse Windows
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Installing LayaBrowse for Windows" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$pythonExe = "python"
if (Test-Path "$env:USERPROFILE\anaconda3\python.exe") {
    $pythonExe = "$env:USERPROFILE\anaconda3\python.exe"
}

Write-Host "Using Python: $pythonExe" -ForegroundColor Green

& $pythonExe -m pip install --upgrade pip
& $pythonExe -m pip install -e .

Write-Host "`nInstallation complete! You can run:" -ForegroundColor Green
Write-Host "  layabrowse doctor   (validate your Windows environment)" -ForegroundColor Yellow
Write-Host "  layabrowse start    (launch voice browser and dynamic island)" -ForegroundColor Yellow
