# tools/tv_setup.ps1
# ===============================================================
# VIZIO SmartCast + EDON Bridge – PowerShell 5.1+
# ===============================================================

# --- trust self-signed certs for SmartCast HTTPS ---
Add-Type @"
using System.Net;
using System.Security.Cryptography.X509Certificates;
public class TrustAllCertsPolicy : ICertificatePolicy {
  public bool CheckValidationResult(ServicePoint srvPoint, X509Certificate certificate, WebRequest request, int certificateProblem) {
    return true;
  }
}
"@ | Out-Null
[System.Net.ServicePointManager]::CertificatePolicy = New-Object TrustAllCertsPolicy

# --- console as UTF-8 (optional pretty output) ---
try { chcp 65001 > $null; $OutputEncoding = [Console]::OutputEncoding = [Text.UTF8Encoding]::new() } catch {}

# --- load SmartCast config (persisted as user env vars) ---
if (-not $env:VIZIO_BASE) { $env:VIZIO_BASE = [Environment]::GetEnvironmentVariable('VIZIO_BASE','User') }
if (-not $env:VIZIO_AUTH) { $env:VIZIO_AUTH = [Environment]::GetEnvironmentVariable('VIZIO_AUTH','User') }

if (-not $env:VIZIO_BASE -or -not $env:VIZIO_AUTH) {
  Write-Warning "VIZIO_BASE or VIZIO_AUTH not found. Pair first, then set env vars."
}

# ===============================================================
# Resilient HTTP wrapper
# ===============================================================
function Invoke-Vizio {
  param(
    [Parameter(Mandatory)] [string] $Path,
    [ValidateSet('GET','PUT')] [string] $Method = 'GET',
    $Body = $null,
    [int] $Retries = 4
  )
  $uri = ($env:VIZIO_BASE.TrimEnd('/')) + $Path
  $delay = 300
  $headers = @{ AUTH = $env:VIZIO_AUTH; Connection = 'close' }
  for($i=1; $i -le $Retries; $i++){
    try {
      if ($Body -ne $null) {
        return Invoke-RestMethod -Method $Method -Uri $uri -Body $Body -ContentType 'application/json' -Headers $headers -TimeoutSec 5
      } else {
        return Invoke-RestMethod -Method $Method -Uri $uri -Headers $headers -TimeoutSec 5
      }
    } catch {
      if ($i -eq $Retries) { throw }
      Start-Sleep -Milliseconds $delay
      $delay = [Math]::Min($delay * 2, 2000)
    }
  }
}

# ===============================================================
# Keypress + App Launchers
# ===============================================================
function Vizio-KeyPress([int]$codeset, [int]$code){
  $body = @{ KEYLIST = @(@{ CODESET=$codeset; CODE=$code; ACTION='KEYPRESS' }) } | ConvertTo-Json -Compress
  Invoke-Vizio -Path "/key_command/" -Method PUT -Body $body | Out-Null
}

function Start-SmartCastApp([int]$Namespace, [string]$AppId, [string]$Message = ""){
  $payload = @{ VALUE = @{ MESSAGE = $Message; NAME_SPACE = $Namespace; APP_ID = $AppId } } | ConvertTo-Json -Compress
  Invoke-Vizio -Path "/app/launch" -Method PUT -Body $payload | Out-Null
}

# --- Core App Launchers ---
function Start-Netflix  { try { Vizio-KeyPress 11 1; Start-Sleep -Milliseconds 600 } catch {}; Start-SmartCastApp -Namespace 3 -AppId "1" }
function Start-YouTubeTV { Start-SmartCastApp -Namespace 5 -AppId "1" }
function Start-PrimeVideo { Start-SmartCastApp -Namespace 2 -AppId "4" }
function Start-Hulu { Start-SmartCastApp -Namespace 2 -AppId "3" }

# ===============================================================
# Health + Warm-up
# ===============================================================
function TV-Health() {
  try { Invoke-Vizio -Path "/state/device/power_mode" -Method GET | Out-Null; return $true } catch { return $false }
}

function TV-WarmUp([int]$tries=4){
  $ok = $false
  1..$tries | ForEach-Object {
    try {
      Invoke-RestMethod -Method GET -Uri "$env:VIZIO_BASE/state/device/power_mode" `
        -Headers @{ AUTH = $env:VIZIO_AUTH; Connection = 'close' } -TimeoutSec 3 | Out-Null
      $ok = $true; break
    } catch { Start-Sleep -Milliseconds 300 }
  }
  return $ok
}

# ===============================================================
# Volume Control (calibration + blind precise setter)
# ===============================================================
$script:CalPath = Join-Path $PSScriptRoot "tv_calibration.json"
if (-not (Get-Variable -Name ShadowVolume -Scope Script -ErrorAction SilentlyContinue)) { $script:ShadowVolume = $null }
if (-not (Get-Variable -Name VolStep      -Scope Script -ErrorAction SilentlyContinue)) { $script:VolStep      = 1.0  }

function Load-TVCalibration {
  try {
    if (Test-Path $script:CalPath) {
      $j = Get-Content $script:CalPath -Raw | ConvertFrom-Json
      if ($j -and $j.VolStep)      { $script:VolStep = [double]$j.VolStep }
      if ($j -and $j.ShadowVolume) { $script:ShadowVolume = [double]$j.ShadowVolume }
      Write-Host ("[CAL] Loaded VolStep={0} Shadow≈{1}" -f $script:VolStep, $script:ShadowVolume)
    }
  } catch { }
}
function Save-TVCalibration {
  try { @{ VolStep = $script:VolStep; ShadowVolume = $script:ShadowVolume } | ConvertTo-Json | Set-Content -Encoding UTF8 $script:CalPath } catch { }
}
Load-TVCalibration

function Nudge-Vol([string]$dir, [int]$steps, [int]$delayMs=110) {
  $code = if ($dir -eq 'up') { 1 } else { 0 }
  1..$steps | ForEach-Object { Vizio-KeyPress 5 $code; Start-Sleep -Milliseconds $delayMs }
}

function Calibrate-TVVolumeManual {
  Write-Host ">>> Calibration will send a few volume presses."
  Write-Host "    After each step, type the on-screen volume number and press Enter."
  Start-Sleep -Milliseconds 400

  Nudge-Vol down 8 150
  $v0 = Read-Host "On-screen volume now (after 8 DOWN)?"
  Nudge-Vol up 10 150
  $v1 = Read-Host "On-screen volume now (after 10 UP)?"
  Nudge-Vol up 10 150
  $v2 = Read-Host "On-screen volume now (after +10 UP more)?"

  try { $v0 = [double]$v0; $v1 = [double]$v1; $v2 = [double]$v2 } catch {
    Write-Warning "Please enter numeric values only. Re-run Calibrate-TVVolumeManual."
    return
  }

  $step1 = ($v1 - $v0) / 10.0
  $step2 = ($v2 - $v1) / 10.0
  $step  = [double]("{0:N2}" -f (([math]::Abs($step1)+[math]::Abs($step2))/2.0))
  if ($step -le 0) { $step = 1.0 }

  $script:VolStep      = $step
  $script:ShadowVolume = $v2
  Save-TVCalibration
  Write-Host ("[CAL] Estimated step ≈ {0} per press; current≈{1}" -f $script:VolStep, $script:ShadowVolume)
  Write-Host "Calibration saved."
}

function Sync-TVVolumeManual([int]$current){ $script:ShadowVolume = [double]$current; Save-TVCalibration }

function Set-TVVolume([int]$target){
  $target = [int][math]::Max(0, [math]::Min(100, $target))
  try {
    $body = @{ VALUE = $target } | ConvertTo-Json -Compress
    Invoke-Vizio -Path "/state/volume/master" -Method PUT -Body $body | Out-Null
    $script:ShadowVolume = [double]$target
    Save-TVCalibration
    Write-Host ("[VOL] Set to {0} (direct PUT)" -f $target)
    return
  } catch { }

  if ($script:ShadowVolume -eq $null) {
    Nudge-Vol 'down' 12 100
    $presses = [int][math]::Ceiling([math]::Abs($target) / [double][math]::Max(1,$script:VolStep))
    while ($presses -gt 0) { $chunk=[Math]::Min(5,$presses); Nudge-Vol 'up' $chunk 120; $presses-=$chunk }
    $script:ShadowVolume = [double]$target
    Save-TVCalibration
    Write-Host ("[VOL] Set to {0} (blind init)" -f $target)
    return
  }

  $err = $target - [int][math]::Round($script:ShadowVolume)
  if ($err -eq 0) { return }

  $perPress = [double][math]::Max(1.0, $script:VolStep)
  $presses  = [int][math]::Max(1,[math]::Round([math]::Abs($err) / $perPress))
  $dir      = if ($err -gt 0) { 'up' } else { 'down' }

  while ($presses -gt 0) {
    $chunk = [int][math]::Min(5,$presses)
    Nudge-Vol $dir $chunk 120
    $presses -= $chunk
  }

  $script:ShadowVolume = [double]$target
  Save-TVCalibration
  Write-Host ("[VOL] Set to {0} (via calibrated step≈{1})" -f $target, $script:VolStep)
}

# ===============================================================
# Power-Off Guard + Mode Mapping
# ===============================================================
if (-not (Get-Variable -Name AllowPowerOff -Scope Script -ErrorAction SilentlyContinue)) { $script:AllowPowerOff = $false }
if (-not (Get-Variable -Name NoOffUntil   -Scope Script -ErrorAction SilentlyContinue)) { $script:NoOffUntil   = Get-Date "2000-01-01" }

function Set-PowerOffGuard([int]$seconds = 30){
  $script:NoOffUntil = (Get-Date).AddSeconds($seconds)
  Write-Host "[TV] Power-off blocked for $seconds seconds."
}

function Vizio-PowerOn { Vizio-KeyPress 11 1; Set-PowerOffGuard 60 }
function Vizio-PowerOff {
  if (-not $script:AllowPowerOff) { Write-Warning "[TV] Power-off suppressed (AllowPowerOff=$AllowPowerOff)"; return }
  if (Get-Date -lt $script:NoOffUntil) { Write-Warning "[TV] Power-off suppressed (cooldown until $NoOffUntil)"; return }
  Vizio-KeyPress 11 0
}

Remove-Item Function:\TV-ActOnMode -ErrorAction SilentlyContinue
function TV-ActOnMode([string]$mode){
  $stamp = Get-Date -Format "HH:mm:ss"
  Write-Host "[TV $stamp] mode=$mode"
  switch ($mode) {
    'focus' {
      Vizio-KeyPress 5 4
    }
    'overload' {
      Write-Host "[TV] overload received (power-off disabled)"
    }
    'restorative' {
      Vizio-PowerOn
      TV-WarmUp | Out-Null
      Start-PrimeVideo      # Change to Netflix / Hulu / YouTubeTV as desired
      Start-Sleep -Milliseconds 600
      Set-TVVolume 15
    }
    default {
      Write-Host "[TV] ignoring unknown mode '$mode'"
    }
  }
}
# ===============================================================
