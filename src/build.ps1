# build.ps1 — GreedyCatBot EXE derleyici
# Çalıştır: .\build.ps1

Write-Host "=== GreedyCatBot EXE Derleme ===" -ForegroundColor Cyan

# PyInstaller kurulu değilse kur
$pi = pip show pyinstaller 2>$null
if (-not $pi) {
    Write-Host "PyInstaller kuruluyor..." -ForegroundColor Yellow
    pip install pyinstaller
}

# Önceki build temizle
if (Test-Path "dist\GreedyCatBot.exe") {
    Remove-Item "dist\GreedyCatBot.exe" -Force
    Write-Host "Eski EXE silindi." -ForegroundColor Gray
}

# Templates klasörü yoksa oluştur (PyInstaller data olarak paketlenir)
if (-not (Test-Path "templates")) {
    New-Item -ItemType Directory -Path "templates" | Out-Null
}

# Derle
Write-Host "Derleniyor..." -ForegroundColor Yellow
pyinstaller GreedyCatBot.spec --clean --noconfirm

if (Test-Path "dist\GreedyCatBot.exe") {
    $size = (Get-Item "dist\GreedyCatBot.exe").Length / 1MB
    Write-Host "" 
    Write-Host "=== BASARILI ===" -ForegroundColor Green
    Write-Host "EXE: dist\GreedyCatBot.exe" -ForegroundColor Green
    Write-Host ("Boyut: {0:F1} MB" -f $size) -ForegroundColor Green
    Write-Host ""
    Write-Host "GitHub Release'e yuklemek icin:" -ForegroundColor Cyan
    Write-Host "  dist\GreedyCatBot.exe dosyasini" -ForegroundColor White
    Write-Host "  https://github.com/yamannerhan/REHA/releases" -ForegroundColor White
    Write-Host "  adresine manuel olarak yukleyin." -ForegroundColor White
} else {
    Write-Host "HATA: EXE olusturulamadi!" -ForegroundColor Red
    Write-Host "Hata detaylari icin yukaridaki loglara bakin." -ForegroundColor Red
}
