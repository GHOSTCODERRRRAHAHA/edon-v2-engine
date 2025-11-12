# tools/edon_tv_watcher.ps1
param(
  [string]$StateUrl = "http://127.0.0.1:8000/_debug/state",
  [int]$IntervalMs = 1000
)

# --- console as UTF-8 + clean banner ---
try { chcp 65001 > $null; $OutputEncoding = [Console]::OutputEncoding = [Text.UTF8Encoding]::new() } catch {}

# --- import TV setup (SmartCast env + functions) ---
. "$PSScriptRoot\tv_setup.ps1"

# --- helper: extract mode from various JSON shapes ---
function Get-ModeFrom($obj) {
  if ($null -eq $obj) { return $null }
  if ($obj.PSObject.Properties.Name -contains 'mode') { return $obj.mode }
  if ($obj.PSObject.Properties.Name -contains 'last_state') {
    $ls = $obj.last_state
    if ($ls -and $ls.PSObject.Properties.Name -contains 'mode') { return $ls.mode }
  }
  if ($obj.PSObject.Properties.Name -contains 'state') {
    $st = $obj.state
    if ($st -and $st.PSObject.Properties.Name -contains 'mode') { return $st.mode }
  }
  # arrays (event logs)
  if ($obj -is [System.Array]) {
    foreach ($e in ($obj | Sort-Object -Descending -Property ts)) {
      if ($e.PSObject.Properties.Name -contains 'mode') { return $e.mode }
    }
  }
  return $null
}

Write-Host " EDON->TV watcher using: $StateUrl  (poll ${IntervalMs}ms)"
$lastMode = $null
$heartbeatEvery = 10     # seconds
$elapsed = 0

while ($true) {
  try {
    $s = Invoke-RestMethod -Uri $StateUrl -TimeoutSec 2
    $mode = Get-ModeFrom $s

    if ($mode -and $mode -ne $lastMode) {
      $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
      Write-Host "[$stamp] mode: $mode -> TV"
      # set lastMode BEFORE calling to avoid spam on error
      $lastMode = $mode
      try { TV-ActOnMode $mode } catch { Write-Warning ("TV call failed: {0}" -f $_.Exception.Message) }
    }
  } catch {
    Write-Warning ("Watcher error: {0}" -f $_.Exception.Message)
  }

  # heartbeat
  $elapsed += ($IntervalMs / 1000.0)
  if ($elapsed -ge $heartbeatEvery) {
    $elapsed = 0
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$stamp] heartbeat (watching $StateUrl)"
  }

  Start-Sleep -Milliseconds $IntervalMs
}
