# --- EDON v0.9 OEM Readiness Verification (ASCII-only) ---
$ErrorActionPreference = "Stop"

function Assert($cond, $msg) {
  if (-not $cond) { throw $msg } else { Write-Host "[OK] $msg" -ForegroundColor Green }
}

# 0) Kill any process bound to :8000 (best-effort)
try {
  Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue |
    ForEach-Object { if ($_.OwningProcess) { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue } }
} catch {}

# 1) Start API via venv Python
$python = Join-Path $PSScriptRoot "venv\Scripts\python.exe"
Assert (Test-Path $python) "Python venv found at venv\Scripts\python.exe"

$uvicornArgs = @("-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8000","--reload")
$api = Start-Process -FilePath $python -ArgumentList $uvicornArgs -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 3

# 2) Health + models/info
$health = Invoke-RestMethod http://127.0.0.1:8000/health
Assert ($health.ok) "Health endpoint OK"
Assert ($health.model.name -and $health.model.sha256) "Model info present on /health"

$info = Invoke-RestMethod http://127.0.0.1:8000/models/info
Assert ($info.name -and $info.sha256 -and $info.pca_dim -and $info.features) "/models/info returns full metadata"

# 3) Build a valid window payload (lowercase keys)
# Build temp array separately (cannot reference $win.temp inside the hashtable literal)
$temp240 = @()
for ($i=0; $i -lt 240; $i++) { $temp240 += 36.5 }

$win = @{
  eda   = @(0..239 | ForEach-Object { 0.01 * $_ })
  temp  = $temp240
  bvp   = @(0..239 | ForEach-Object { [Math]::Sin($_ * 0.1) })
  acc_x = @(0..239 | ForEach-Object { 0.0 })
  acc_y = @(0..239 | ForEach-Object { 0.0 })
  acc_z = @(0..239 | ForEach-Object { 1.0 })
}

$body = @{
  windows = @(
    @{
      eda=$win.eda; temp=$win.temp; bvp=$win.bvp;
      acc_x=$win.acc_x; acc_y=$win.acc_y; acc_z=$win.acc_z;
      temp_c=22; humidity=45; aqi=40; local_hour=14
    }
  )
} | ConvertTo-Json -Depth 8

$r = Invoke-RestMethod -Uri "http://127.0.0.1:8000/oem/cav/batch" -Method POST -Body $body -ContentType "application/json"
Assert ($r -and $r.Count -ge 1) "Batch endpoint accepts lowercase keys"

# 4) Rate limit (expect at least one 429 after threshold)
$rc200 = 0; $rc429 = 0
for ($i=1; $i -le 70; $i++) {
  try {
    Invoke-RestMethod -Uri "http://127.0.0.1:8000/oem/cav/batch" -Method POST -Body $body -ContentType "application/json" | Out-Null
    $rc200++
  } catch {
    $resp = $_.Exception.Response
    if ($resp -and $resp.StatusCode.value__ -eq 429) { $rc429++ } else { throw "Unexpected HTTP error at request $i" }
  }
}
Assert ($rc429 -ge 1) "Rate limiting enforced (429 observed)"

# 5) Metrics sample
$metrics = (Invoke-WebRequest http://127.0.0.1:8000/metrics).Content
$sample = ($metrics -split "`n" | Select-Object -First 12) -join "`n"
Write-Host "[INFO] Metrics sample:" -ForegroundColor Cyan
Write-Host $sample
Assert ($metrics -match "process_cpu_seconds_total") "Prometheus metrics exposed"

# 6) Build dataset + check MANIFEST.json
& $python tools\build_oem_dataset_fast.py --out data\oem_v09_demo | Out-Host
Assert (Test-Path "data\oem_v09_demo\MANIFEST.json") "Dataset MANIFEST.json created"
Write-Host "[INFO] MANIFEST.json:" -ForegroundColor Cyan
Get-Content data\oem_v09_demo\MANIFEST.json | Out-Host

# 7) Tests (quick suite)
& $python -m pytest -q tests\test_v09_checklist.py
if ($LASTEXITCODE -ne 0) { throw "Test suite failed" } else { Write-Host "[OK] Test suite passed" -ForegroundColor Green }

# 8) Optional: edge offline replay test
if (Test-Path tests\test_edge_offline.py) {
  & $python -m pytest -q tests\test_edge_offline.py
  if ($LASTEXITCODE -ne 0) { throw "Edge offline replay test failed" } else { Write-Host "[OK] Edge offline replay passed" -ForegroundColor Green }
}

Write-Host ""
Write-Host "EDON v0.9 OEM-READY - all checks passed." -ForegroundColor Green
