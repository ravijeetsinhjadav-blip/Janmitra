Set-Location 'E:\Janmitra\JanMitra_Assist_Final_Submission'
Write-Host "Testing portable launcher sanity from:" (Get-Location)
$BackendDir = Join-Path (Get-Location) "Source_Code\backend"
$AdminDir   = Join-Path (Get-Location) "Source_Code\admin_dashboard"
$MobileDir  = Join-Path (Get-Location) "Source_Code\mobile_app"
$WebRelease = Join-Path (Get-Location) "Web_Release\Flutter_Web"
$AdminRelease = Join-Path (Get-Location) "Web_Release\Admin_Dashboard"

Write-Host "Backend Dir exists:" (Test-Path $BackendDir)
Write-Host "Admin Dir exists:" (Test-Path $AdminDir)
Write-Host "Mobile Dir exists:" (Test-Path $MobileDir)
Write-Host "Web Release exists:" (Test-Path $WebRelease)
Write-Host "Admin Release exists:" (Test-Path $AdminRelease)

# Test prebuilt bundle contents
Write-Host "Admin index.html exists:" (Test-Path (Join-Path $AdminRelease "index.html"))
Write-Host "Flutter Web index.html exists:" (Test-Path (Join-Path $WebRelease "index.html"))

# Test HTTP server capability on prebuilt bundles
Write-Host "Testing Python HTTP server readiness on prebuilts..."
$testPort = 8099
$p = Start-Process "python" -ArgumentList "-m http.server $testPort --directory `"$WebRelease`"" -PassThru
Start-Sleep -Seconds 2
try {
    $resp = Invoke-WebRequest -Uri "http://127.0.0.1:$testPort/index.html" -TimeoutSec 2
    Write-Host "Prebuilt Flutter Web HTTP Status:" $resp.StatusCode
} finally {
    Stop-Process -Id $p.Id -Force
}
