param(
    [string]$installDir = "C:\Program Files\CodePass"
)

$manifestUrl = "https://raw.githubusercontent.com/codepass0v12/Codepass/main/update.json"
Write-Host "📥 Pobieranie manifestu aktualizacji z $manifestUrl..."

try {
    $manifest = Invoke-RestMethod -Uri $manifestUrl -UseBasicParsing
    $zipUrl = $manifest.download_url
    $sigUrl = $manifest.sig_url
    $version = $manifest.version
    $zipPath = "$env:TEMP\update_$version.zip"
    $sigPath = "$env:TEMP\update_$version.sig"

    Write-Host "📦 Pobieranie paczki v$version..."
    Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath
    Invoke-WebRequest -Uri $sigUrl -OutFile $sigPath

    Write-Host "🧩 Weryfikacja podpisu..."
    $publicKeyPath = Join-Path $installDir "public_key.pem"

    $verifyScript = @"
import base64, sys
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

with open(r'$publicKeyPath','rb') as f:
    key = serialization.load_pem_public_key(f.read(), backend=default_backend())

with open(r'$zipPath','rb') as f:
    data = f.read()

with open(r'$sigPath','rb') as f:
    sig = f.read()

try:
    key.verify(sig, data, padding.PKCS1v15(), hashes.SHA256())
    print("OK")
except Exception as e:
    print("FAIL", e)
"@

    $pyTemp = "$env:TEMP\verify.py"
    $verifyScript | Out-File -Encoding utf8 -FilePath $pyTemp
    $verify = python $pyTemp

    if ($verify -notmatch "OK") {
        Write-Host "❌ Błąd weryfikacji podpisu."
        exit 1
    }

    Write-Host "✅ Podpis poprawny. Rozpakowywanie..."
    Expand-Archive -Path $zipPath -DestinationPath $installDir -Force
    Write-Host "✅ Zainstalowano CodePass v$version w $installDir"

    Remove-Item $zipPath, $sigPath, $pyTemp -ErrorAction SilentlyContinue
}
catch {
    Write-Host "❌ Wystąpił błąd: $($_.Exception.Message)"
    exit 1
}
